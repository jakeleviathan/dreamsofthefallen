from __future__ import annotations

from datetime import datetime

from mud.character_options import CLASSES_BY_KEY, RACES_BY_KEY
from mud.database import MAX_CHARACTERS_PER_ACCOUNT
from mud.security import hash_password, verify_password
from mud.world import ROOMS_BY_KEY


GOTHIC_WELCOME_BANNER = "\r\n".join(
    [
        "",
        "                 /\\                 /\\                 /\\",
        "                /  \\      /\\       /  \\       /\\      /  \\",
        "           ____/____\\____/  \\_____/____\\_____/  \\____/____\\____",
        "          /                                                         \\",
        "         /   .---------------------------------------------------.   \\",
        "        |    |                                                   |    |",
        "        |    |              DREAMS OF THE FALLEN                 |    |",
        "        |    |                     ASTRALIS                      |    |",
        "        |    |                                                   |    |",
        "         \\   '---------------------------------------------------'   /",
        "          \\_________________________________________________________/",
        "                     |      |      |      |      |",
        "                  ___|______|______|______|______|___",
        "",
        "                   Beneath Astralis, something dreams.",
        "",
        "                         LOGIN     CREATE ACCOUNT",
        "",
        "                   Type HELP for a brief explanation.",
        "",
    ]
) + "\r\n"

LANDING_HELP = (
    "\r\nLOGIN - sign in to an existing account.\r\n"
    "CREATE ACCOUNT - make a new account. You will enter your password twice.\r\n"
    "QUIT - leave Dreams of the Fallen.\r\n"
)

ACCOUNT_NAME_RULES = (
    "Account names must be 3-20 characters, begin with a letter, and contain only letters, numbers, or underscores."
)


def _valid_account_name(player_session_class, account_name: str) -> bool:
    # Reuse the authoritative pattern from mud.session so the UI cannot drift
    # away from the actual account-name rules.
    import mud.session as session_module

    return bool(session_module.ACCOUNT_NAME_PATTERN.fullmatch(account_name))


def _ensure_last_played_column(database) -> None:
    """Keep older development databases compatible with the polished roster."""
    with database.connect() as db:
        columns = {row["name"] for row in db.execute("PRAGMA table_info(characters)").fetchall()}
        if "last_played_at" not in columns:
            db.execute("ALTER TABLE characters ADD COLUMN last_played_at TEXT")


def _last_played_value(database, character_id: int) -> str | None:
    _ensure_last_played_column(database)
    with database.connect() as db:
        row = db.execute(
            "SELECT last_played_at FROM characters WHERE id = ?",
            (character_id,),
        ).fetchone()
    if row is None:
        return None
    return row["last_played_at"]


def _touch_last_played(database, character_id: int) -> None:
    _ensure_last_played_column(database)
    with database.connect() as db:
        db.execute(
            "UPDATE characters SET last_played_at = CURRENT_TIMESTAMP WHERE id = ?",
            (character_id,),
        )


def format_last_played(value: str | None) -> str:
    if not value:
        return "Never"
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return value
    return parsed.strftime("%Y-%m-%d %H:%M UTC")


def _find_roster_character(characters, target: str):
    normalized = target.strip().lower()
    if normalized.isdigit():
        slot = int(normalized)
        if 1 <= slot <= len(characters):
            return characters[slot - 1]
        return None
    return next((character for character in characters if character.name.lower() == normalized), None)


def _location_name(character) -> str:
    if not character.current_room:
        return "Not entered yet"
    room = ROOMS_BY_KEY.get(character.current_room)
    return room.name if room is not None else character.current_room.replace("_", " ").title()


def _most_recent_character(database, characters):
    candidates = []
    for character in characters:
        value = _last_played_value(database, character.id)
        if value:
            candidates.append((value, character))
    if not candidates:
        return None
    return max(candidates, key=lambda item: item[0])[1]


def install_login_experience(player_session_class) -> None:
    """Replace the pre-character Telnet flow with the approved screen-by-screen UX."""
    if getattr(player_session_class, "_login_experience_installed", False):
        return

    import mud.session as session_module

    session_module.WELCOME_BANNER = GOTHIC_WELCOME_BANNER

    async def account_name_screen(self) -> None:
        command = await self.prompt("Entry: ")
        if command is None:
            self.state = session_module.SessionState.DISCONNECTED
            return

        normalized = command.strip().lower()
        if normalized in {"login", "log in", "l"}:
            await self.login_flow(None)
            return
        if normalized in {"create", "create account", "new account", "new"}:
            await self.create_account_flow(None)
            return
        if normalized in {"help", "?"}:
            await self.send(LANDING_HELP)
            return
        if normalized in {"quit", "q", "exit"}:
            await self.send("\r\nThe connection closes. Somewhere beyond it, Astralis waits.\r\n")
            self.state = session_module.SessionState.DISCONNECTED
            return

        await self.send("\r\nType LOGIN or CREATE ACCOUNT. Type HELP if you need the short version.\r\n\r\n")

    async def create_account_flow(self, account_name: str | None = None) -> None:
        if account_name is None:
            await self.send(
                "\r\n--- Create Account ---\r\n"
                "Your account name identifies the account itself, not a character.\r\n"
            )
            account_name = await self.prompt("Account name: ")
            if account_name is None:
                self.state = session_module.SessionState.DISCONNECTED
                return

        account_name = account_name.strip()
        if not _valid_account_name(player_session_class, account_name):
            await self.send(ACCOUNT_NAME_RULES + "\r\n\r\n")
            return
        if self.database.get_account_by_name(account_name) is not None:
            await self.send(
                f"\r\nAn account named '{account_name}' already exists. Use LOGIN instead.\r\n\r\n"
            )
            return

        while True:
            password = await self.prompt("Choose a password (at least 8 characters): ")
            if password is None:
                self.state = session_module.SessionState.DISCONNECTED
                return
            if len(password) < 8:
                await self.send("Your password must be at least 8 characters long. Please try again.\r\n")
                continue

            confirmation = await self.prompt("Confirm password: ")
            if confirmation is None:
                self.state = session_module.SessionState.DISCONNECTED
                return
            if confirmation != password:
                await self.send(
                    "The passwords did not match. Please enter the password again.\r\n"
                )
                continue
            break

        try:
            self.account = self.database.create_account(account_name, hash_password(password))
        except Exception:
            await self.send(
                "\r\nThat account name became unavailable before creation finished. Please choose another.\r\n\r\n"
            )
            return

        self.database.mark_login(self.account.id)
        await self.send(
            f"\r\nAccount '{self.account.name}' created successfully.\r\n"
            "Your character roster is ready.\r\n"
        )
        self.state = session_module.SessionState.CHARACTER_MENU

    async def login_flow(self, account=None) -> None:
        if account is None:
            await self.send("\r\n--- Login ---\r\n")
            account_name = await self.prompt("Account name: ")
            if account_name is None:
                self.state = session_module.SessionState.DISCONNECTED
                return
            account_name = account_name.strip()
            if not _valid_account_name(player_session_class, account_name):
                await self.send(ACCOUNT_NAME_RULES + "\r\n\r\n")
                return
            account = self.database.get_account_by_name(account_name)
            if account is None:
                await self.send(
                    f"\r\nNo account named '{account_name}' exists. Use CREATE ACCOUNT to make one.\r\n\r\n"
                )
                return

        password = await self.prompt("Password: ")
        if password is None:
            self.state = session_module.SessionState.DISCONNECTED
            return
        if not verify_password(password, account.password_hash):
            await self.send("\r\nIncorrect password. Returning to the opening screen.\r\n\r\n")
            return

        self.account = account
        self.database.mark_login(account.id)
        await self.send(f"\r\nWelcome back, {account.name}.\r\n")
        self.state = session_module.SessionState.CHARACTER_MENU

    async def character_menu(self) -> None:
        assert self.account is not None
        characters = self.database.list_characters(self.account.id)
        used_slots = len(characters)
        remaining_slots = max(0, MAX_CHARACTERS_PER_ACCOUNT - used_slots)
        recent_character = _most_recent_character(self.database, characters)

        await self.send(
            "\r\n+--------------------------------------------------------------------------------------+\r\n"
            "|                                   CHARACTER ROSTER                                   |\r\n"
            "+--------------------------------------------------------------------------------------+\r\n"
        )
        for slot in range(1, MAX_CHARACTERS_PER_ACCOUNT + 1):
            if slot <= used_slots:
                character = characters[slot - 1]
                race = RACES_BY_KEY.get(character.race or "")
                character_class = CLASSES_BY_KEY.get(character.character_class or "")
                race_name = race.name if race else (character.race or "Unknown")
                class_name = character_class.name if character_class else (character.character_class or "Unknown")
                last_played = format_last_played(_last_played_value(self.database, character.id))
                location = _location_name(character)
                await self.send(
                    f"| {slot}. {character.name:<18} Lv {character.level:<3} {race_name:<12} {class_name:<12}                      |\r\n"
                    f"|    Location: {location:<36} Last: {last_played:<23} |\r\n"
                )
            else:
                await self.send(f"| {slot}. [ Empty ]{' ' * 69}|\r\n")
        await self.send(
            "+--------------------------------------------------------------------------------------+\r\n"
            f"Slots used: {used_slots}/{MAX_CHARACTERS_PER_ACCOUNT}"
            + (f"    Empty slots: {remaining_slots}\r\n" if remaining_slots else "    Character slots are full.\r\n")
        )
        if recent_character is not None:
            await self.send(f"Last played: {recent_character.name}\r\n")
        await self.send("Commands: ENTER <slot or name>    PLAY LAST    CREATE    QUIT\r\n")

        choice = await self.prompt("Roster: ")
        if choice is None:
            self.state = session_module.SessionState.DISCONNECTED
            return

        normalized = choice.strip()
        lowered = normalized.lower()
        if lowered in {"help", "?"}:
            await self.send(
                "\r\nENTER <slot or name> - play an existing character.\r\n"
                "PLAY LAST - immediately enter the character you played most recently.\r\n"
                "CREATE - begin making a new character in an empty slot.\r\n"
                "QUIT - disconnect.\r\n"
            )
            return
        if lowered in {"quit", "q", "exit"}:
            await self.send("\r\nGoodbye.\r\n")
            self.state = session_module.SessionState.DISCONNECTED
            return
        if lowered in {"create", "new", "new character", "c"}:
            if remaining_slots <= 0:
                await self.send(
                    f"\r\nAll {MAX_CHARACTERS_PER_ACCOUNT} character slots are already in use.\r\n"
                )
                return
            # Re-check at action time for simultaneous sessions on one account.
            if len(self.database.list_characters(self.account.id)) >= MAX_CHARACTERS_PER_ACCOUNT:
                await self.send(
                    f"\r\nAll {MAX_CHARACTERS_PER_ACCOUNT} character slots are already in use.\r\n"
                )
                return
            await self.character_creation_flow()
            return
        if lowered in {"play last", "last", "resume", "continue"}:
            if recent_character is None:
                await self.send(
                    "\r\nThere is no previously played character on this account yet. Use ENTER or CREATE.\r\n"
                )
                return
            _touch_last_played(self.database, recent_character.id)
            self.character = recent_character
            await self.enter_character()
            return

        target = normalized
        if lowered.startswith("enter "):
            target = normalized.split(maxsplit=1)[1].strip()
        elif lowered == "enter":
            await self.send("\r\nUse ENTER <slot or character name>.\r\n")
            return

        # Bare slot numbers and exact character names remain accepted so the
        # roster is friendly to both old MUD habits and the explicit ENTER form.
        character = _find_roster_character(characters, target)
        if character is None:
            await self.send("\r\nThat character slot is empty or no character by that name exists.\r\n")
            return

        _touch_last_played(self.database, character.id)
        self.character = character
        await self.enter_character()

    player_session_class.account_name_screen = account_name_screen
    player_session_class.create_account_flow = create_account_flow
    player_session_class.login_flow = login_flow
    player_session_class.character_menu = character_menu
    player_session_class._login_experience_installed = True
