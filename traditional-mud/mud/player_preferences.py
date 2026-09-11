from __future__ import annotations

from dataclasses import dataclass


PROMPT_MODES = frozenset({"quiet", "compact", "full"})
COLOR_MODES = frozenset({"auto", "on", "off"})
CONTRAST_MODES = frozenset({"standard", "high"})
HINT_LEVELS = frozenset({"off", "gentle", "full"})


@dataclass(frozen=True, slots=True)
class PlayerPreferences:
    prompt_mode: str = "compact"
    color_mode: str = "auto"
    contrast_mode: str = "standard"
    hint_level: str = "gentle"
    mudlet_enhancements: bool = True
    screen_reader: bool = False


DEFAULT_PREFERENCES = PlayerPreferences()


def _ensure_schema(database) -> None:
    with database.connect() as db:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS account_preferences (
                account_id INTEGER PRIMARY KEY,
                prompt_mode TEXT NOT NULL DEFAULT 'compact',
                color_mode TEXT NOT NULL DEFAULT 'auto',
                contrast_mode TEXT NOT NULL DEFAULT 'standard',
                hint_level TEXT NOT NULL DEFAULT 'gentle',
                mudlet_enhancements INTEGER NOT NULL DEFAULT 1,
                screen_reader INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
            )
            """
        )


def _account_id(session) -> int | None:
    account = getattr(session, "account", None)
    account_id = getattr(account, "id", None)
    return int(account_id) if account_id is not None else None


def _coerce_preferences(row) -> PlayerPreferences:
    if row is None:
        return DEFAULT_PREFERENCES
    prompt = str(row["prompt_mode"] or "compact").lower()
    color = str(row["color_mode"] or "auto").lower()
    contrast = str(row["contrast_mode"] or "standard").lower()
    hints = str(row["hint_level"] or "gentle").lower()
    return PlayerPreferences(
        prompt_mode=prompt if prompt in PROMPT_MODES else "compact",
        color_mode=color if color in COLOR_MODES else "auto",
        contrast_mode=contrast if contrast in CONTRAST_MODES else "standard",
        hint_level=hints if hints in HINT_LEVELS else "gentle",
        mudlet_enhancements=bool(row["mudlet_enhancements"]),
        screen_reader=bool(row["screen_reader"]),
    )


def _apply_to_session(session, preferences: PlayerPreferences) -> None:
    session._player_prompt_mode_preference = preferences.prompt_mode
    session._player_color_mode = preferences.color_mode
    session._player_contrast_mode = preferences.contrast_mode
    session._player_hint_level = preferences.hint_level
    session._mudlet_enhancements_enabled = preferences.mudlet_enhancements
    session._screen_reader_enabled = preferences.screen_reader
    # Screen-reader mode is a runtime accessibility override. It does not destroy
    # the player's saved prompt choice, so turning it off restores that choice.
    session._room_ux_prompt_mode = "quiet" if preferences.screen_reader else preferences.prompt_mode


def load_preferences(session, *, force: bool = False) -> PlayerPreferences:
    account_id = _account_id(session)
    database = getattr(session, "database", None)
    if account_id is None or database is None:
        preferences = DEFAULT_PREFERENCES
        _apply_to_session(session, preferences)
        return preferences

    if not force and getattr(session, "_preferences_loaded_account_id", None) == account_id:
        return PlayerPreferences(
            prompt_mode=str(getattr(session, "_player_prompt_mode_preference", "compact")),
            color_mode=str(getattr(session, "_player_color_mode", "auto")),
            contrast_mode=str(getattr(session, "_player_contrast_mode", "standard")),
            hint_level=str(getattr(session, "_player_hint_level", "gentle")),
            mudlet_enhancements=bool(getattr(session, "_mudlet_enhancements_enabled", True)),
            screen_reader=bool(getattr(session, "_screen_reader_enabled", False)),
        )

    _ensure_schema(database)
    with database.connect() as db:
        db.execute(
            "INSERT OR IGNORE INTO account_preferences (account_id) VALUES (?)",
            (account_id,),
        )
        row = db.execute(
            """
            SELECT prompt_mode, color_mode, contrast_mode, hint_level,
                   mudlet_enhancements, screen_reader
            FROM account_preferences
            WHERE account_id = ?
            """,
            (account_id,),
        ).fetchone()
    preferences = _coerce_preferences(row)
    session._preferences_loaded_account_id = account_id
    _apply_to_session(session, preferences)
    return preferences


def _set_preference(session, column: str, value) -> PlayerPreferences:
    account_id = _account_id(session)
    database = getattr(session, "database", None)
    if account_id is None or database is None:
        raise RuntimeError("Player preferences require a logged-in account.")
    allowed_columns = {
        "prompt_mode",
        "color_mode",
        "contrast_mode",
        "hint_level",
        "mudlet_enhancements",
        "screen_reader",
    }
    if column not in allowed_columns:
        raise ValueError(f"Unsupported preference: {column}")
    _ensure_schema(database)
    with database.connect() as db:
        db.execute(
            "INSERT OR IGNORE INTO account_preferences (account_id) VALUES (?)",
            (account_id,),
        )
        db.execute(
            f"UPDATE account_preferences SET {column} = ? WHERE account_id = ?",
            (value, account_id),
        )
    return load_preferences(session, force=True)


def persist_prompt_mode(session, mode: str) -> None:
    normalized = mode.lower()
    if normalized not in PROMPT_MODES:
        raise ValueError("Invalid prompt mode")
    try:
        _set_preference(session, "prompt_mode", normalized)
    except RuntimeError:
        session._player_prompt_mode_preference = normalized
        session._room_ux_prompt_mode = normalized


def hint_level(session) -> str:
    level = str(getattr(session, "_player_hint_level", "gentle")).lower()
    return level if level in HINT_LEVELS else "gentle"


def mudlet_enhancements_enabled(session) -> bool:
    if bool(getattr(session, "_screen_reader_enabled", False)):
        return False
    return bool(getattr(session, "_mudlet_enhancements_enabled", True))


def color_enabled(session) -> bool:
    if bool(getattr(session, "_screen_reader_enabled", False)):
        return False
    mode = str(getattr(session, "_player_color_mode", "auto")).lower()
    if mode == "off":
        return False
    if mode == "on":
        return True
    telnet = getattr(session, "telnet", None)
    return bool(getattr(telnet, "gmcp_enabled", False))


def style_text(session, text: str, role: str = "accent") -> str:
    """Apply restrained ANSI styling only when the player has opted into it.

    AUTO stays plain for generic Telnet and becomes colored for a GMCP-capable
    client such as Mudlet. Screen-reader mode always returns plain text.
    """
    if not color_enabled(session):
        return text
    high = str(getattr(session, "_player_contrast_mode", "standard")).lower() == "high"
    if high:
        code = "1;97" if role == "heading" else "1;96"
    else:
        code = "1;36" if role == "heading" else "36"
    return f"\x1b[{code}m{text}\x1b[0m"


def _setting_lines(preferences: PlayerPreferences) -> str:
    return (
        "\r\n--- Settings & Accessibility ---\r\n"
        f"Prompt: {preferences.prompt_mode.upper()}\r\n"
        f"Color: {preferences.color_mode.upper()}\r\n"
        f"Contrast: {preferences.contrast_mode.upper()}\r\n"
        f"Hints: {preferences.hint_level.upper()}\r\n"
        f"Mudlet enhancements: {'ON' if preferences.mudlet_enhancements else 'OFF'}\r\n"
        f"Screen reader mode: {'ON' if preferences.screen_reader else 'OFF'}\r\n"
        "\r\n"
        "SET PROMPT QUIET|COMPACT|FULL\r\n"
        "SET COLOR AUTO|ON|OFF\r\n"
        "SET CONTRAST STANDARD|HIGH\r\n"
        "SET HINTS OFF|GENTLE|FULL\r\n"
        "SET MUDLET ON|OFF\r\n"
        "SET SCREENREADER ON|OFF\r\n"
        "SETTINGS RESET - restore recommended defaults\r\n"
        "\r\n"
        "Defaults are intentionally simple: compact prompt, gentle hints, color only in capable clients, and Mudlet enhancements enabled.\r\n"
    )


async def _delegate_command(self, previous_playing_prompt, command: str) -> None:
    had_instance_prompt = "prompt" in self.__dict__
    prior_prompt = self.__dict__.get("prompt")

    async def replay_prompt(_text: str) -> str:
        return command

    self.prompt = replay_prompt
    try:
        await previous_playing_prompt(self)
    finally:
        if had_instance_prompt:
            self.prompt = prior_prompt
        else:
            self.__dict__.pop("prompt", None)


def _on_off(value: str) -> bool | None:
    lowered = value.lower()
    if lowered in {"on", "yes", "true", "1"}:
        return True
    if lowered in {"off", "no", "false", "0"}:
        return False
    return None


async def _handle_set_command(session, normalized: str) -> bool:
    parts = normalized.split()
    if len(parts) < 3 or parts[0] != "set":
        return False
    key = parts[1]
    value = " ".join(parts[2:])

    if key == "prompt":
        if value not in PROMPT_MODES:
            await session.send("Choose SET PROMPT QUIET, COMPACT, or FULL.\r\n")
            return True
        _set_preference(session, "prompt_mode", value)
        await session.send(f"Prompt set to {value.upper()} and saved for this account.\r\n")
        return True

    if key == "color":
        if value not in COLOR_MODES:
            await session.send("Choose SET COLOR AUTO, ON, or OFF.\r\n")
            return True
        _set_preference(session, "color_mode", value)
        await session.send(f"Color set to {value.upper()}.\r\n")
        return True

    if key == "contrast":
        if value not in CONTRAST_MODES:
            await session.send("Choose SET CONTRAST STANDARD or HIGH.\r\n")
            return True
        _set_preference(session, "contrast_mode", value)
        await session.send(f"Contrast set to {value.upper()}.\r\n")
        return True

    if key in {"hints", "hint"}:
        if value not in HINT_LEVELS:
            await session.send("Choose SET HINTS OFF, GENTLE, or FULL.\r\n")
            return True
        _set_preference(session, "hint_level", value)
        await session.send(f"Automatic hints set to {value.upper()}.\r\n")
        return True

    if key == "mudlet":
        enabled = _on_off(value)
        if enabled is None:
            await session.send("Choose SET MUDLET ON or OFF.\r\n")
            return True
        _set_preference(session, "mudlet_enhancements", 1 if enabled else 0)
        if enabled:
            # Allow a newly re-enabled session to receive the normal Client.GUI offer.
            session.mudlet_gui_offer_sent = False
        await session.send(
            f"Mudlet enhancements {'enabled' if enabled else 'disabled'}. "
            "This controls server-supplied HUD offers and GMCP state; it does not uninstall a package already installed in your client.\r\n"
        )
        return True

    if key in {"screenreader", "screen-reader", "screen", "screen reader"}:
        enabled = _on_off(value)
        if enabled is None:
            await session.send("Choose SET SCREENREADER ON or OFF.\r\n")
            return True
        preferences = _set_preference(session, "screen_reader", 1 if enabled else 0)
        if enabled:
            await session.send(
                "Screen reader mode enabled. ANSI color and server-supplied Mudlet state are suppressed, and the live prompt becomes quiet.\r\n"
            )
        else:
            await session.send(
                f"Screen reader mode disabled. Your saved {preferences.prompt_mode.upper()} prompt and other preferences are restored.\r\n"
            )
        return True

    return False


def install_player_preferences_runtime(player_session_class) -> None:
    """Install persistent account-level presentation and accessibility settings."""
    if getattr(player_session_class, "_player_preferences_runtime_installed", False):
        return

    previous_enter_character = getattr(player_session_class, "enter_character", None)
    if previous_enter_character is not None:
        async def enter_character(self) -> None:
            await previous_enter_character(self)
            load_preferences(self, force=True)

        player_session_class.enter_character = enter_character

    previous_offer = getattr(player_session_class, "offer_official_mudlet_hud", None)
    if previous_offer is not None:
        async def offer_official_mudlet_hud(self) -> bool:
            if getattr(self, "account", None) is not None:
                load_preferences(self)
            if not mudlet_enhancements_enabled(self):
                return False
            return await previous_offer(self)

        player_session_class.offer_official_mudlet_hud = offer_official_mudlet_hud

    previous_state = getattr(player_session_class, "send_client_state", None)
    if previous_state is not None:
        async def send_client_state(self) -> None:
            if getattr(self, "account", None) is not None:
                load_preferences(self)
            if not mudlet_enhancements_enabled(self):
                return
            await previous_state(self)

        player_session_class.send_client_state = send_client_state

    previous_playing_prompt = player_session_class.playing_prompt

    async def playing_prompt(self) -> None:
        if getattr(self, "character", None) is None:
            await previous_playing_prompt(self)
            return

        load_preferences(self)
        command = await self.prompt("\r\n> ")
        if command is None:
            state = getattr(self, "state", None)
            if state is not None and hasattr(type(state), "DISCONNECTED"):
                self.state = type(state).DISCONNECTED
            return
        normalized = " ".join(command.strip().lower().split())

        if normalized in {"settings", "setting", "preferences", "prefs", "accessibility"}:
            await self.send(_setting_lines(load_preferences(self)))
            return
        if normalized in {"settings reset", "preferences reset", "prefs reset"}:
            account_id = _account_id(self)
            if account_id is None:
                await self.send("Settings are available after login.\r\n")
                return
            _ensure_schema(self.database)
            with self.database.connect() as db:
                db.execute("DELETE FROM account_preferences WHERE account_id = ?", (account_id,))
            self._preferences_loaded_account_id = None
            preferences = load_preferences(self, force=True)
            await self.send("Settings restored to the recommended defaults.\r\n")
            await self.send(_setting_lines(preferences))
            return
        if await _handle_set_command(self, normalized):
            return

        await _delegate_command(self, previous_playing_prompt, command)

    player_session_class.playing_prompt = playing_prompt
    player_session_class._player_preferences_runtime_installed = True
