from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any

GAME_NAME = "Dreams of the Fallen"
DISCORD_PROTOCOL_VERSION = 1
PARTY_MAX_DEFAULT = 5

# Asset names to create in the Discord developer application. Mudlet requires
# icon names to be lowercase and accepts an ordered fallback list.
CLASS_ASSET_NAMES = {
    "brute": "class-brute",
    "wizard": "class-wizard",
    "necromancer": "class-necromancer",
    "druid": "class-druid",
    "priest": "class-priest",
}

_SENSITIVE_TAG_FRAGMENTS = ("secret", "hidden", "spoiler", "puzzle", "undiscovered")
_SENSITIVE_KEY_FRAGMENTS = ("secret", "hidden")
_MAX_TEXT = 128


def _clean_text(value: Any, *, limit: int = _MAX_TEXT) -> str:
    text = " ".join(str(value or "").replace("\r", " ").replace("\n", " ").split())
    if len(text) <= limit:
        return text
    return text[: max(1, limit - 1)].rstrip() + "…"


def _title_key(value: str | None) -> str:
    return _clean_text(str(value or "").replace("_", " ").title())


def _room_is_sensitive(room: Any) -> bool:
    if room is None:
        return False
    key = str(getattr(room, "key", "") or "").lower()
    tags = tuple(str(tag).lower() for tag in (getattr(room, "tags", ()) or ()))
    return any(fragment in key for fragment in _SENSITIVE_KEY_FRAGMENTS) or any(
        fragment in tag
        for tag in tags
        for fragment in _SENSITIVE_TAG_FRAGMENTS
    )


@dataclass(frozen=True, slots=True)
class DiscordPresenceConfig:
    application_id: str = ""
    invite_url: str = ""
    game_name: str = GAME_NAME

    @property
    def info_payload(self) -> dict[str, str]:
        payload: dict[str, str] = {}
        if self.application_id:
            payload["applicationid"] = self.application_id
        if self.invite_url:
            payload["inviteurl"] = self.invite_url
        return payload


def configured_discord_presence() -> DiscordPresenceConfig:
    application_id = os.getenv("DREAMS_DISCORD_APPLICATION_ID", "").strip()
    # Discord application IDs are decimal snowflakes. Refuse malformed values
    # rather than sending a broken application identifier to every client.
    if application_id and not application_id.isdigit():
        application_id = ""

    invite_url = os.getenv("DREAMS_DISCORD_INVITE_URL", "").strip()
    if invite_url and not invite_url.startswith(("https://discord.gg/", "https://discord.com/invite/")):
        invite_url = ""

    return DiscordPresenceConfig(
        application_id=application_id,
        invite_url=invite_url,
    )


class DiscordPresenceService:
    """Build spoiler-conscious External.Discord GMCP payloads.

    The service owns formatting, de-duplication, activity priority, and privacy
    boundaries so Discord integration does not get scattered through gameplay
    code. It deliberately never stores the Discord username supplied in
    External.Discord.Hello.
    """

    def __init__(
        self,
        config: DiscordPresenceConfig | None = None,
        *,
        started_at: int | None = None,
    ) -> None:
        self.config = config or configured_discord_presence()
        self.started_at = int(started_at if started_at is not None else time.time())
        self.ready = False
        self._last_status: dict[str, Any] | None = None
        self.activity_kind = ""
        self.activity_label = ""

    def set_activity(self, kind: str, label: str = "") -> None:
        self.activity_kind = _clean_text(kind, limit=32).lower()
        self.activity_label = _clean_text(label)

    def clear_activity(self) -> None:
        self.activity_kind = ""
        self.activity_label = ""

    def info_payload(self) -> dict[str, str]:
        return self.config.info_payload

    def _party_counts(self, session: Any) -> tuple[int, int]:
        try:
            from mud import party_system

            party = party_system._party_for_session(session)
            if party is None:
                return 0, 0
            return len(party.member_ids), int(getattr(party_system, "PARTY_MAX_MEMBERS", PARTY_MAX_DEFAULT))
        except Exception:
            return 0, 0

    def _active_quest(self, session: Any) -> tuple[str, str] | None:
        character = getattr(session, "character", None)
        database = getattr(session, "database", None)
        if character is None or database is None:
            return None
        try:
            from mud.quests import QUESTS_BY_KEY

            rows = database.list_quests(character.id)
        except Exception:
            return None

        for row in rows:
            if str(row.get("status") or "").lower() != "active":
                continue
            key = str(row.get("quest_key") or "")
            definition = QUESTS_BY_KEY.get(key)
            if definition is None:
                return (_title_key(key), "")
            return (_clean_text(definition.name), str(definition.style or ""))
        return None

    def build_status(self, session: Any) -> dict[str, Any]:
        character = getattr(session, "character", None)
        if character is None:
            return {
                "smallimage": ["server-icon"],
                "smallimagetext": GAME_NAME,
                "details": "At the threshold of Astralis",
                "state": "Choosing a character",
                "partysize": 0,
                "partymax": 0,
                "game": self.config.game_name,
                "starttime": str(self.started_at),
            }

        try:
            from mud.character_options import CLASSES_BY_KEY, RACES_BY_KEY
            from mud.world import ROOMS_BY_KEY
            from mud.world_data import REGIONS_BY_KEY
        except Exception:
            CLASSES_BY_KEY = {}
            RACES_BY_KEY = {}
            ROOMS_BY_KEY = {}
            REGIONS_BY_KEY = {}

        class_key = str(getattr(character, "character_class", "") or "")
        race_key = str(getattr(character, "race", "") or "")
        level = int(getattr(character, "level", 1) or 1)
        class_definition = CLASSES_BY_KEY.get(class_key)
        race_definition = RACES_BY_KEY.get(race_key)
        class_name = _clean_text(getattr(class_definition, "name", "") or _title_key(class_key) or "Adventurer")
        race_name = _clean_text(getattr(race_definition, "name", "") or _title_key(race_key) or "Adventurer")

        room_key = str(getattr(character, "current_room", "") or "")
        room = None
        # Production installs a large amount of authored content dynamically
        # into the shared WorldService after mud.world is imported. Resolve the
        # live scene first so Rich Presence covers the assembled game instead
        # of only the legacy static room dictionary.
        try:
            from mud.room_runtime import WORLD as LIVE_WORLD
            room = LIVE_WORLD.scene(room_key)
        except Exception:
            room = None
        if room is None:
            room = ROOMS_BY_KEY.get(room_key)
        sensitive = _room_is_sensitive(room)
        room_name = _clean_text(getattr(room, "name", "") or "Astralis")
        region = REGIONS_BY_KEY.get(str(getattr(room, "region_key", "") or "")) if room is not None else None
        region_name = _clean_text(getattr(region, "name", "") or "Astralis")

        active_enemy = getattr(session, "active_enemy", None)
        quest = self._active_quest(session)
        party_size, party_max = self._party_counts(session)

        details = f"Level {level} {race_name} {class_name}"
        if quest is not None and not sensitive:
            quest_name, quest_style = quest
            if quest_style.lower() != "discovery" and quest_name:
                details = _clean_text(f"{details} • {quest_name}")

        if active_enemy is not None:
            if sensitive:
                state = "Battling an unknown threat somewhere forgotten"
            else:
                enemy_name = _clean_text(getattr(getattr(active_enemy, "definition", None), "name", "") or "an enemy")
                state = _clean_text(f"Battling {enemy_name} • {room_name}")
        elif self.activity_kind == "crafting":
            state = _clean_text(f"Crafting {self.activity_label}" if self.activity_label else "Crafting in Astralis")
        elif self.activity_kind == "gathering":
            state = _clean_text(f"Gathering {self.activity_label}" if self.activity_label else "Gathering in Astralis")
        elif self.activity_kind == "questing" and self.activity_label and not sensitive:
            state = _clean_text(f"Questing: {self.activity_label}")
        elif sensitive:
            state = "Exploring somewhere forgotten in Astralis"
        elif room is not None:
            state = _clean_text(f"Exploring {room_name} • {region_name}")
        else:
            state = "Exploring Astralis"

        asset = CLASS_ASSET_NAMES.get(class_key, "server-icon")
        image_fallbacks = [asset]
        if class_key and class_key != asset:
            image_fallbacks.append(class_key.lower())
        if "server-icon" not in image_fallbacks:
            image_fallbacks.append("server-icon")

        return {
            "smallimage": image_fallbacks,
            "smallimagetext": _clean_text(f"{class_name} • Level {level}"),
            "details": _clean_text(details),
            "state": _clean_text(state),
            "partysize": party_size,
            "partymax": party_max,
            "game": self.config.game_name,
            "starttime": str(self.started_at),
        }

    def status_if_changed(self, session: Any, *, force: bool = False) -> dict[str, Any] | None:
        status = self.build_status(session)
        if not force and status == self._last_status:
            return None
        self._last_status = dict(status)
        return status
