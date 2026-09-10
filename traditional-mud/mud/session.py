from __future__ import annotations

import asyncio
import random
import re
from enum import Enum, auto

from mud.character_options import (
    CLASSES,
    CLASSES_BY_KEY,
    RACES,
    RACES_BY_KEY,
    ClassDefinition,
    RaceDefinition,
)
from mud.crafting import (
    ALL_RECIPES,
    GATHERING_SKILLS,
    ITEMS_BY_KEY,
    PROFESSIONS,
    TAILORING_RECIPES,
    craft_recipe,
)
from mud.database import (
    AccountRecord,
    CharacterRecord,
    CharacterSlotLimitReached,
    Database,
    MAX_CHARACTERS_PER_ACCOUNT,
)
from mud.security import hash_password, verify_password
from mud.stats import (
    CharacterStats,
    STARTING_STAT_RULES,
    STAT_KEYS,
    STATS_BY_KEY,
    build_starting_stats,
    starting_stat_baseline,
    starting_armor_class,
)
from mud.mechanics import (
    CombatantState,
    FIXED_CLASS_ABILITIES,
    PRIEST_DEITIES,
    PRIEST_DEITIES_BY_KEY,
    PRIEST_DEITY_RULES,
    PROGRESSION_RULES,
    DEATH_RULES,
    class_abilities_for_level,
)
from mud.world_data import REGIONS_BY_KEY
from mud.quests import (
    HUMAN_CATHEDRAL_SUMMONS,
    HUMAN_COMBAT_TRAINING,
    HUMAN_LOWER_WARDS_INVESTIGATION,
    FOREST_ELF_FIRST_WALK,
    SPOREKIN_FIRST_CALL,
    SPOREKIN_FORGOTTEN_PULSE,
    QUESTS_BY_KEY,
)
from mud.world import (
    HUMAN_PRACTICE_RING_KEY,
    HUMAN_START_ROOM_KEY,
    HUMAN_TRAINING_YARD_KEY,
    HUMAN_VERMIN_PENS_KEY,
    HUMAN_SOOTSTAIRS_KEY,
    HUMAN_BLACKGLASS_ARCH_KEY,
    HUMAN_LANTERN_COURT_KEY,
    FOREST_ELF_START_ROOM_KEY,
    FOREST_ELF_OLD_RIVER_PATH_KEY,
    FOREST_ELF_WAYSTONE_BEND_KEY,
    FOREST_ELF_LISTENING_POOL_KEY,
    FOREST_ELF_OUTER_GROVE_KEY,
    SPOREKIN_START_ROOM_KEY,
    SPOREKIN_SURFACEWARD_ROOM_KEY,
    SPOREKIN_SURFACE_VERGE_ROOM_KEY,
    SPOREKIN_FORGOTTEN_GROVE_ROOM_KEY,
    SPOREKIN_MEMORY_PATH_ROOM_KEY,
    NPCS_BY_KEY,
    ROOMS_BY_KEY,
)
from mud.combat import ENEMIES_BY_KEY, EnemyDefinition, EnemyState, FLEE_RULES
from mud.npcs import MobileNpcManager, NpcMovement
from mud.telnet import TelnetConnection
from mud.client_gui import MudletGuiOffer, configured_mudlet_gui_offer
from mud.merchants import MERCHANTS_BY_NPC_KEY


class SessionState(Enum):
    ACCOUNT_NAME = auto()
    CHARACTER_MENU = auto()
    PLAYING = auto()
    DISCONNECTED = auto()


WELCOME_BANNER = "\r\n".join([
    '',
    '                         /\\          /\\',
    '                    /\\  /  \\  /\\    /  \\',
    '                   /  \\/ /\\ \\/  \\__/ /\\ \\',
    '              ____/________________________\\____',
    '             /    _   _   _   _   _   _        \\',
    '            /____/ \\_/ \\_/ \\_/ \\_/ \\_/ \\_______\\',
    '            |                               |',
    '            |       DREAMS OF THE FALLEN    |',
    '            |            ASTRALIS           |',
    '            |_______________________________|',
    '                |   |   |   |   |   |',
    '             ___|___|___|___|___|___|___',
    '            /_____________________________\\',
    '',
    '              Where the dead still dream.',
    '',
]) + "\r\n"

ACCOUNT_NAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_]{2,19}$")


class PlayerSession:
    def __init__(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        database: Database,
        mobile_npcs: MobileNpcManager | None = None,
        mobile_npc_movement_callback=None,
        mudlet_gui_offer: MudletGuiOffer | None = None,
    ) -> None:
        self.reader = reader
        self.writer = writer
        self.database = database
        self.mobile_npcs = mobile_npcs
        self.mobile_npc_movement_callback = mobile_npc_movement_callback
        self.state = SessionState.ACCOUNT_NAME
        self.peer = writer.get_extra_info("peername")
        self.account: AccountRecord | None = None
        self.character: CharacterRecord | None = None
        self.combatant: CombatantState | None = None
        self.active_enemy: EnemyState | None = None
        self.active_mobile_npc_key: str | None = None
        self.combat_task: asyncio.Task | None = None
        self.ward_until: float = 0.0
        self.dot_tasks: set[asyncio.Task] = set()
        self.telnet = TelnetConnection(reader, writer)
        self.mudlet_gui_offer = mudlet_gui_offer or configured_mudlet_gui_offer()
        self.mudlet_gui_offer_sent = False

    async def send(self, text: str) -> None:
        await self.telnet.send_text(text)

    async def prompt(self, text: str) -> str | None:
        await self.send(text)
        line = await self.telnet.read_line()
        await self.offer_official_mudlet_hud()
        return line

    async def offer_official_mudlet_hud(self) -> bool:
        """Offer the official HUD once Mudlet/GMCP negotiation is active.

        Mudlet's Client.GUI extension downloads and installs the package when
        the player has allowed server-supplied script packages. The MUD never
        attempts to bypass that client-side security preference.
        """
        if self.mudlet_gui_offer_sent:
            return False
        if not self.telnet.gmcp_enabled or not self.mudlet_gui_offer.enabled:
            return False
        sent = await self.telnet.send_gmcp(
            "Client.GUI",
            {
                "version": self.mudlet_gui_offer.version,
                "url": self.mudlet_gui_offer.url,
            },
        )
        if sent:
            self.mudlet_gui_offer_sent = True
        return sent

    async def send_client_state(self) -> None:
        """Push live out-of-band vitals to GMCP-capable clients such as Mudlet.

        Mudlet 5.x can use Char.Vitals/Char.Status to construct its Base UI
        automatically. We intentionally omit XP from this packet so the four
        useful live gauges remain HP, mana, movement, and enemy health.
        """
        if self.character is None or self.combatant is None or not self.telnet.gmcp_enabled:
            return

        target = self.active_enemy
        vitals = {
            "hp": self.combatant.current_hp,
            "maxhp": self.combatant.max_hp,
            "mana": self.combatant.current_mana,
            "maxmana": self.combatant.max_mana,
            "movement": self.combatant.current_movement,
            "maxmovement": self.combatant.max_movement,
        }
        if target is not None:
            vitals.update({
                "enemy_health": target.current_hp,
                "enemy_max_health": target.definition.max_hp,
                "opponent_health": target.current_hp,
                "opponent_health_max": target.definition.max_hp,
            })

        status = {
            "name": self.character.name,
            "level": self.character.level,
            "race": self.character.race or "",
            "class": self.character.character_class or "",
            "enemy_name": target.definition.name if target is not None else "",
            "opponent_name": target.definition.name if target is not None else "",
            "enemy_health": target.current_hp if target is not None else 0,
            "enemy_max_health": target.definition.max_hp if target is not None else 0,
            "opponent_health": target.current_hp if target is not None else 0,
            "opponent_health_max": target.definition.max_hp if target is not None else 0,
        }
        await self.telnet.send_gmcp("Char.Maxstats", {
            "maxhp": self.combatant.max_hp,
            "maxmana": self.combatant.max_mana,
            "maxmovement": self.combatant.max_movement,
        })
        await self.telnet.send_gmcp("Char.Vitals", vitals)
        await self.telnet.send_gmcp("Char.Status", status)
        await self.telnet.send_gmcp("Dreams.Vitals", {
            "hp": self.combatant.current_hp,
            "max_hp": self.combatant.max_hp,
            "mana": self.combatant.current_mana,
            "max_mana": self.combatant.max_mana,
            "movement": self.combatant.current_movement,
            "max_movement": self.combatant.max_movement,
        })
        await self.telnet.send_gmcp("Dreams.Target", {
            "name": target.definition.name if target is not None else "",
            "hp": target.current_hp if target is not None else 0,
            "max_hp": target.definition.max_hp if target is not None else 0,
            "active": target is not None,
        })

    async def run(self) -> None:
        print(f"Connected: {self.peer}")
        try:
            await self.telnet.begin_negotiation()
            await self.send(WELCOME_BANNER)
            while self.state is not SessionState.DISCONNECTED:
                if self.state is SessionState.ACCOUNT_NAME:
                    await self.account_name_screen()
                elif self.state is SessionState.CHARACTER_MENU:
                    await self.character_menu()
                elif self.state is SessionState.PLAYING:
                    await self.playing_prompt()
        except (ConnectionError, asyncio.IncompleteReadError):
            pass
        finally:
            await self.close()
            print(f"Disconnected: {self.peer}")

    async def account_name_screen(self) -> None:
        account_name = await self.prompt("Account name: ")
        if account_name is None:
            self.state = SessionState.DISCONNECTED
            return

        if not ACCOUNT_NAME_PATTERN.fullmatch(account_name):
            await self.send(
                "Account names must be 3-20 characters, begin with a letter, "
                "and contain only letters, numbers, or underscores.\r\n\r\n"
            )
            return

        existing = self.database.get_account_by_name(account_name)
        if existing is None:
            await self.create_account_flow(account_name)
        else:
            await self.login_flow(existing)

    async def create_account_flow(self, account_name: str) -> None:
        answer = await self.prompt(
            f"\r\nNo account named '{account_name}' exists. Create it? (Y/N): "
        )
        if answer is None:
            self.state = SessionState.DISCONNECTED
            return
        if answer.lower() not in {"y", "yes"}:
            await self.send("\r\n")
            return

        while True:
            password = await self.prompt("Choose a password: ")
            if password is None:
                self.state = SessionState.DISCONNECTED
                return
            if len(password) < 8:
                await self.send("Password must be at least 8 characters long.\r\n")
                continue

            confirmation = await self.prompt("Confirm password: ")
            if confirmation is None:
                self.state = SessionState.DISCONNECTED
                return
            if confirmation != password:
                await self.send("Passwords did not match. Try again.\r\n")
                continue
            break

        try:
            self.account = self.database.create_account(
                account_name,
                hash_password(password),
            )
        except Exception:
            # A second connection may have claimed the same account name between
            # the availability check and INSERT. Return safely to the login screen.
            await self.send(
                "\r\nThat account name became unavailable. Please try again.\r\n\r\n"
            )
            return

        self.database.mark_login(self.account.id)
        await self.send(f"\r\nAccount '{self.account.name}' created.\r\n")
        self.state = SessionState.CHARACTER_MENU

    async def login_flow(self, account: AccountRecord) -> None:
        password = await self.prompt("Password: ")
        if password is None:
            self.state = SessionState.DISCONNECTED
            return

        if not verify_password(password, account.password_hash):
            await self.send("\r\nIncorrect password.\r\n\r\n")
            return

        self.account = account
        self.database.mark_login(account.id)
        await self.send(f"\r\nWelcome back, {account.name}.\r\n")
        self.state = SessionState.CHARACTER_MENU

    async def character_menu(self) -> None:
        assert self.account is not None
        characters = self.database.list_characters(self.account.id)

        used_slots = len(characters)
        remaining_slots = max(0, MAX_CHARACTERS_PER_ACCOUNT - used_slots)

        await self.send(
            f"\r\n--- Characters ({used_slots}/{MAX_CHARACTERS_PER_ACCOUNT} slots used) ---\r\n"
        )
        if characters:
            for index, character in enumerate(characters, start=1):
                race = RACES_BY_KEY.get(character.race or "")
                character_class = CLASSES_BY_KEY.get(character.character_class or "")
                race_name = race.name if race else (character.race or "Unknown")
                class_name = character_class.name if character_class else (character.character_class or "Unknown")
                await self.send(
                    f"{index}) {character.name:<16} Level {character.level:<3} {race_name} {class_name}\r\n"
                )
        else:
            await self.send("You do not have any characters yet.\r\n")

        next_number = len(characters) + 1
        create_number: int | None = None
        if remaining_slots > 0:
            create_number = next_number
            next_number += 1
            await self.send(
                f"{create_number}) Create a new character "
                f"({remaining_slots} slot{'s' if remaining_slots != 1 else ''} remaining)\r\n"
            )
        else:
            await self.send("Character slots full. Maximum: 8.\r\n")

        quit_number = next_number
        await self.send(f"{quit_number}) Quit\r\n")

        choice = await self.prompt("\r\nSelection: ")
        if choice is None:
            self.state = SessionState.DISCONNECTED
            return

        if create_number is not None and choice == str(create_number):
            # Re-check the database at selection time so simultaneous sessions on the
            # same account cannot bypass the eight-character account limit.
            current_count = len(self.database.list_characters(self.account.id))
            if current_count >= MAX_CHARACTERS_PER_ACCOUNT:
                await self.send(
                    f"\r\nAll {MAX_CHARACTERS_PER_ACCOUNT} character slots are already in use.\r\n"
                )
                return

            await self.character_creation_flow()
            return

        if choice == str(quit_number) or choice.lower() in {"q", "quit"}:
            await self.send("\r\nGoodbye.\r\n")
            self.state = SessionState.DISCONNECTED
            return

        if choice.isdigit() and 1 <= int(choice) <= len(characters):
            self.character = characters[int(choice) - 1]
            await self.enter_character()
            return

        await self.send("\r\nInvalid selection.\r\n")


    async def enter_character(self) -> None:
        assert self.character is not None
        race = RACES_BY_KEY.get(self.character.race or "")
        character_class = CLASSES_BY_KEY.get(self.character.character_class or "")
        region = REGIONS_BY_KEY.get(race.starting_region or "") if race else None

        # Human characters are the first race with a fully authored room-by-room
        # starting sequence. This also upgrades Human characters created by older
        # development builds so they receive the same introduction safely.
        if self.character.race == "human":
            if not self.character.current_room:
                self.database.set_character_room(self.character.id, HUMAN_START_ROOM_KEY)
            if self.database.item_quantity(self.character.id, "sealed_cathedral_note") <= 0:
                quest = self.database.get_quest(self.character.id, HUMAN_CATHEDRAL_SUMMONS.key)
                if quest is None or quest.get("status") != "completed":
                    self.database.add_item(self.character.id, "sealed_cathedral_note", 1)
            if self.database.get_quest(self.character.id, HUMAN_CATHEDRAL_SUMMONS.key) is None:
                self.database.start_quest(self.character.id, HUMAN_CATHEDRAL_SUMMONS.key, "read_note")
            refreshed = self.database.get_character_by_name(self.character.name)
            if refreshed is not None:
                self.character = refreshed

        # Forest Elves begin inside an isolated forest town and receive a
        # Druidic Circle exploration walk. Older development characters without
        # a room or quest are upgraded into the same opening safely.
        if self.character.race == "forest_elf":
            if not self.character.current_room:
                self.database.set_character_room(self.character.id, FOREST_ELF_START_ROOM_KEY)
            if self.database.get_quest(self.character.id, FOREST_ELF_FIRST_WALK.key) is None:
                self.database.start_quest(
                    self.character.id, FOREST_ELF_FIRST_WALK.key, "leave_clearing"
                )
            refreshed = self.database.get_character_by_name(self.character.name)
            if refreshed is not None:
                self.character = refreshed

        # Sporekin now have an authored room-based opening as well. Older
        # development characters without a room are placed at the same start.
        if self.character.race == "sporekin":
            if not self.character.current_room:
                self.database.set_character_room(self.character.id, SPOREKIN_START_ROOM_KEY)
            first_call = self.database.get_quest(self.character.id, SPOREKIN_FIRST_CALL.key)
            if first_call is None:
                self.database.start_quest(
                    self.character.id, SPOREKIN_FIRST_CALL.key, "follow_living_threads"
                )
            elif (
                first_call.get("status") == "completed"
                and "sporekin_first_call_answered" in self.database.list_flags(self.character.id)
                and self.database.get_quest(self.character.id, SPOREKIN_FORGOTTEN_PULSE.key) is None
            ):
                self.database.start_quest(
                    self.character.id, SPOREKIN_FORGOTTEN_PULSE.key, "cross_veil"
                )
            refreshed = self.database.get_character_by_name(self.character.name)
            if refreshed is not None:
                self.character = refreshed

        # Bind point is persistent and independent of current location. Newly
        # authored starting rooms become the default bind unless a spell later
        # changes it.
        if not self.character.bind_room and self.character.current_room in ROOMS_BY_KEY:
            self.database.set_bind_room(self.character.id, self.character.current_room)
            refreshed = self.database.get_character_by_name(self.character.name)
            if refreshed is not None:
                self.character = refreshed

        # HP/mana are session combat state. Death now returns the character to
        # their persistent bind point and applies the authored XP penalty.
        self.combatant = CombatantState(
            character_id=self.character.id,
            race_key=self.character.race or "",
            current_hp=self.character.stats.maximum_hp(25),
            max_hp=self.character.stats.maximum_hp(25),
            current_mana=self.character.stats.maximum_mana(20),
            max_mana=self.character.stats.maximum_mana(20),
            auto_attack_interval=2.5,
            current_movement=100,
            max_movement=100,
            stats=self.character.stats,
            armor_class=starting_armor_class(self.character.character_class or ""),
        )

        await self.send("\r\n==================================================\r\n")
        await self.send(f"Entering Astralis as {self.character.name}.\r\n")
        if race and character_class:
            await self.send(f"{race.name} {character_class.name} - Level {self.character.level}\r\n")

        if self.character.current_room in ROOMS_BY_KEY:
            await self.send("\r\n")
            await self.show_current_room()
            if self.character.race == "human":
                quest = self.database.get_quest(self.character.id, HUMAN_CATHEDRAL_SUMMONS.key)
                if quest and quest.get("status") == "active" and quest.get("current_step") == "read_note":
                    await self.send(
                        "\r\nA sealed note rests among your belongings. Type INVENTORY, then READ NOTE.\r\n"
                    )
            elif self.character.race == "forest_elf":
                quest = self.database.get_quest(self.character.id, FOREST_ELF_FIRST_WALK.key)
                if quest and quest.get("status") == "active" and quest.get("current_step") == "leave_clearing":
                    await self.send(
                        "\r\nA simple charge from the local Druidic Circle returns to mind:\r\n"
                        "\r\n  Walk the old river path. Do not hurry. Learn the forest before you ask it to answer you.\r\n"
                        "  Follow the carved leaf. Listen where the water grows still. Go only as far as the boundary oak.\r\n"
                        "\r\nNew quest: The Old River Path. Type QUESTS to review the Circle's instruction.\r\n"
                    )
            elif self.character.race == "sporekin":
                quest = self.database.get_quest(self.character.id, SPOREKIN_FIRST_CALL.key)
                if quest and quest.get("status") == "active" and quest.get("current_step") == "follow_living_threads":
                    await self.send(
                        "\r\nA thought enters you without sound. It is intimate, familiar, and unmistakably plural.\r\n"
                        "\r\n  You are awake. We feel you.\r\n"
                        "  Follow the living threads north. Rise toward the breathing world.\r\n"
                        "  You do not leave us when you walk alone.\r\n"
                        "\r\nNew quest: The Chorus Beneath. Type QUESTS to review the call.\r\n"
                    )
            await self.send("Type HELP for commands.\r\n")
        else:
            if region:
                await self.send(f"Starting region: {region.name}\r\n")
                await self.send(f"{region.description}\r\n")
            await self.send(
                "\r\nThis race's room-by-room starting area has not been authored yet. "
                "The existing playable systems remain available here.\r\n"
                "Type HELP for commands.\r\n"
            )
        self.state = SessionState.PLAYING
        await self.send_client_state()

    async def show_current_room(self) -> None:
        assert self.character is not None
        room = ROOMS_BY_KEY.get(self.character.current_room or "")
        if room is None:
            race = RACES_BY_KEY.get(self.character.race or "")
            region = REGIONS_BY_KEY.get(race.starting_region or "") if race else None
            if region:
                await self.send(f"{region.name}\r\n{region.description}\r\n")
            return

        await self.send(f"{room.name}\r\n")
        await self.send(f"{room.description}\r\n")
        for npc_key in room.npc_keys:
            npc = NPCS_BY_KEY.get(npc_key)
            if npc:
                await self.send(f"\r\n{npc.name} is here, {npc.short_description}.\r\n")
        for enemy_key in room.enemy_keys:
            enemy = ENEMIES_BY_KEY.get(enemy_key)
            if enemy:
                await self.send(f"\r\n{enemy.name} is here, {enemy.description}.\r\n")
        if self.mobile_npcs is not None:
            for state in self.mobile_npcs.npcs_in_room(room.key):
                await self.send(
                    f"\r\n{state.definition.name} is here, {state.definition.short_description}.\r\n"
                )
        exits = list(room.exits.keys())
        if (
            room.key == SPOREKIN_FORGOTTEN_GROVE_ROOM_KEY
            and "sporekin_forgotten_pulse_solved" in self.database.list_flags(self.character.id)
        ):
            await self.send(
                "\r\nA faint spore-shaped sigil hangs above the roots, pointing north toward a newly revealed path.\r\n"
            )
            exits.append("north")
        if exits:
            await self.send("Exits: " + ", ".join(exits) + "\r\n")

    async def move_character(self, direction: str) -> None:
        assert self.character is not None
        if self.active_enemy is not None:
            await self.send("You are fighting. Use FLEE before leaving the room.\r\n")
            return
        room = ROOMS_BY_KEY.get(self.character.current_room or "")
        if room is None:
            await self.send("There are no authored exits from this area yet.\r\n")
            return
        destination_key = room.exits.get(direction)
        if (
            destination_key is None
            and room.key == SPOREKIN_FORGOTTEN_GROVE_ROOM_KEY
            and direction == "north"
            and "sporekin_forgotten_pulse_solved" in self.database.list_flags(self.character.id)
        ):
            destination_key = SPOREKIN_MEMORY_PATH_ROOM_KEY
        if destination_key is None:
            await self.send("You cannot go that way.\r\n")
            return
        self.database.set_character_room(self.character.id, destination_key)
        refreshed = self.database.get_character_by_name(self.character.name)
        if refreshed is not None:
            self.character = refreshed
        await self.send("\r\n")
        await self.show_current_room()
        await self.check_mobile_npc_aggression()

        training = self.database.get_quest(self.character.id, HUMAN_COMBAT_TRAINING.key)
        if (
            destination_key == HUMAN_TRAINING_YARD_KEY
            and training
            and training.get("status") == "active"
            and training.get("current_step") == "reach_training_yard"
        ):
            self.database.advance_quest(self.character.id, HUMAN_COMBAT_TRAINING.key, "practice_dummy")
            await self.send("Quest updated: Lessons Beyond the Gate. Enter the Practice Ring to the north.\r\n")

        lower_wards = self.database.get_quest(self.character.id, HUMAN_LOWER_WARDS_INVESTIGATION.key)
        if (
            lower_wards
            and lower_wards.get("status") == "active"
            and lower_wards.get("current_step") == "find_lower_wards"
            and destination_key == HUMAN_SOOTSTAIRS_KEY
        ):
            self.database.advance_quest(self.character.id, HUMAN_LOWER_WARDS_INVESTIGATION.key, "inspect_mark")
            await self.send(
                "\r\nThe sounds of Ashen Way recede above you. Down here, the city's polished mask gives way to soot, old brick, and guarded voices. "
                "The High Acolyte mentioned a mark that had begun appearing near sealed passages. Find it.\r\n"
                "Quest updated: Marks in the Ash.\r\n"
            )

        forest_walk = self.database.get_quest(self.character.id, FOREST_ELF_FIRST_WALK.key)
        if forest_walk and forest_walk.get("status") == "active":
            step = forest_walk.get("current_step")
            if destination_key == "forest_elf_greenway" and step == "leave_clearing":
                self.database.advance_quest(self.character.id, FOREST_ELF_FIRST_WALK.key, "follow_river")
                await self.send(
                    "\r\nThe town sounds fade behind you. The Circle's instruction is simple: follow the Greenway east until you find the river.\r\n"
                    "Quest updated: The Old River Path.\r\n"
                )
            elif destination_key == FOREST_ELF_WAYSTONE_BEND_KEY and step in {"follow_river", "study_waystone"}:
                self.database.advance_quest(self.character.id, FOREST_ELF_FIRST_WALK.key, "study_waystone")
                await self.send(
                    "\r\nThe leaf-and-circle emblem on the old stone matches the Circle's instruction. EXAMINE WAYSTONE before continuing.\r\n"
                    "Quest updated: The Old River Path.\r\n"
                )
            elif destination_key == FOREST_ELF_OUTER_GROVE_KEY and step == "reach_outer_grove":
                self.database.complete_quest(self.character.id, FOREST_ELF_FIRST_WALK.key)
                self.database.grant_flag(self.character.id, "forest_elf_first_walk_completed")
                await self.send(
                    "\r\nThe red cloth and old claw marks on the boundary oak explain the Circle's lesson without ceremony: beauty and danger share the same forest.\r\n"
                    "\r\nQuest complete: The Old River Path.\r\n"
                )

        sporekin_call = self.database.get_quest(self.character.id, SPOREKIN_FIRST_CALL.key)
        if sporekin_call and sporekin_call.get("status") == "active":
            step = sporekin_call.get("current_step")
            if destination_key == "sporekin_mycelial_gallery" and step == "follow_living_threads":
                self.database.advance_quest(self.character.id, SPOREKIN_FIRST_CALL.key, "follow_cool_air")
                await self.send(
                    "\r\nThe living network beneath your feet seems to tighten around a single shared thought:\r\n"
                    "\r\n  Good. Feel the cooler air. Follow it east. The roots remember the way upward.\r\n"
                    "\r\nQuest updated: The Chorus Beneath.\r\n"
                )
            elif destination_key == "sporekin_rootwell_ascent" and step == "follow_cool_air":
                self.database.advance_quest(self.character.id, SPOREKIN_FIRST_CALL.key, "climb_toward_light")
                await self.send(
                    "\r\nThe chorus brushes the edge of your thoughts again, softer now:\r\n"
                    "\r\n  Above you is rain, leaf, wind, and the voices of those who do not hear us. Climb.\r\n"
                    "\r\nQuest updated: The Chorus Beneath.\r\n"
                )
            elif destination_key == SPOREKIN_SURFACEWARD_ROOM_KEY and step == "climb_toward_light":
                self.database.complete_quest(self.character.id, SPOREKIN_FIRST_CALL.key)
                self.database.grant_flag(self.character.id, "sporekin_first_call_answered")
                self.database.start_quest(self.character.id, SPOREKIN_FORGOTTEN_PULSE.key, "cross_veil")
                await self.send(
                    "\r\nAt the edge of the filtered daylight, the many voices become one calm certainty:\r\n"
                    "\r\n  Here is the veil. Beyond it, Astralis speaks in countless separate voices.\r\n"
                    "  Learn them. Guide when you can. Listen always. We remain beneath you.\r\n"
                    "\r\nQuest complete: The Chorus Beneath.\r\n"
                    "\r\nThen another sensation surfaces beneath the chorus: older, weaker, almost forgotten.\r\n"
                    "\r\n  There is a memory near the rain. Cross the veil. Find the ring that still remembers us.\r\n"
                    "\r\nNew quest: The Forgotten Pulse.\r\n"
                )

        forgotten_pulse = self.database.get_quest(self.character.id, SPOREKIN_FORGOTTEN_PULSE.key)
        if forgotten_pulse and forgotten_pulse.get("status") == "active":
            step = forgotten_pulse.get("current_step")
            if destination_key == SPOREKIN_SURFACE_VERGE_ROOM_KEY and step == "cross_veil":
                self.database.advance_quest(self.character.id, SPOREKIN_FORGOTTEN_PULSE.key, "find_grove")
                await self.send(
                    "\r\nRain touches you for the first time. Through the shared consciousness comes only a faint direction: east, toward an old pulse.\r\n"
                    "Quest updated: The Forgotten Pulse.\r\n"
                )
            elif destination_key == SPOREKIN_FORGOTTEN_GROVE_ROOM_KEY and step == "find_grove":
                self.database.advance_quest(self.character.id, SPOREKIN_FORGOTTEN_PULSE.key, "study_ring")
                await self.send(
                    "\r\nThe collective falls almost silent here. This memory is too old to be spoken clearly. Study the mushroom ring itself.\r\n"
                    "Quest updated: The Forgotten Pulse.\r\n"
                )

    async def _stop_combat(self, *, disengage_mobile_npc: bool = True) -> None:
        task = self.combat_task
        self.combat_task = None
        mobile_key = self.active_mobile_npc_key
        self.active_enemy = None
        self.active_mobile_npc_key = None
        if disengage_mobile_npc and mobile_key and self.mobile_npcs is not None and self.character is not None:
            self.mobile_npcs.disengage(mobile_key, self.character.id)
        if task is not None and task is not asyncio.current_task() and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        for dot_task in tuple(self.dot_tasks):
            if dot_task is asyncio.current_task() or dot_task.done():
                continue
            dot_task.cancel()
        self.dot_tasks = {dot_task for dot_task in self.dot_tasks if not dot_task.done()}

    async def _handle_character_death(self, enemy_name: str) -> None:
        """Apply XP loss and return the character to their persistent bind point."""
        assert self.character is not None and self.combatant is not None

        loss_requested, level_floor = DEATH_RULES.experience_loss(
            self.character.level, self.character.experience
        )
        actual_loss, _new_xp, _new_level = self.database.apply_experience_loss(
            self.character.id,
            loss_requested,
            floor_experience=level_floor if not DEATH_RULES.allow_level_loss else 0,
        )

        bind_room = self.character.bind_room
        if not bind_room or bind_room not in ROOMS_BY_KEY:
            # Development safety for races whose authored room starts do not yet
            # exist. Once a valid room exists, it becomes the default bind.
            bind_room = (
                self.character.current_room
                if self.character.current_room in ROOMS_BY_KEY
                else HUMAN_START_ROOM_KEY
            )
            self.database.set_bind_room(self.character.id, bind_room)

        await self.send(f"\r\n*** You have been slain by {enemy_name}. ***\r\n")
        if actual_loss > 0:
            await self.send(f"You lose {actual_loss} experience.\r\n")
        else:
            await self.send("You have no experience progress to lose at this level.\r\n")

        self.database.set_character_room(self.character.id, bind_room)
        self.combatant.current_hp = self.combatant.max_hp
        self.combatant.current_mana = self.combatant.max_mana
        await self._stop_combat()

        refreshed = self.database.get_character_by_name(self.character.name)
        if refreshed is not None:
            self.character = refreshed

        room = ROOMS_BY_KEY.get(bind_room)
        room_name = room.name if room else bind_room
        await self.send(
            f"A familiar pull gathers what remains of you and returns you to your bind point: {room_name}.\r\n\r\n"
        )
        if room is not None:
            await self.show_current_room()
        await self.send_client_state()

    async def _finish_enemy_defeat(self, enemy: EnemyState) -> None:
        assert self.character is not None
        if self.active_enemy is not enemy:
            return
        enemy_name = enemy.definition.name
        xp = enemy.definition.xp_reward
        await self.send(f"\r\n{enemy_name} is defeated.\r\n")
        if xp > 0:
            previous_level = self.character.level
            new_level = self.database.add_experience(self.character.id, xp)
            await self.send(f"You gain {xp} experience.\r\n")
            refreshed = self.database.get_character_by_name(self.character.name)
            if refreshed is not None:
                self.character = refreshed
            if new_level > previous_level:
                await self.send(f"*** You have reached level {new_level}! ***\r\n")

        training = self.database.get_quest(self.character.id, HUMAN_COMBAT_TRAINING.key)
        if training and training.get("status") == "active":
            step = training.get("current_step")
            if enemy.definition.key == "training_dummy" and step == "practice_dummy":
                self.database.grant_flag(self.character.id, "human_training_dummy_defeated")
                self.database.advance_quest(self.character.id, HUMAN_COMBAT_TRAINING.key, "defeat_vermin")
                await self.send("Quest updated: Lessons Beyond the Gate. Now defeat a Sewer Rat or Small Imp in the Vermin Pens.\r\n")
            elif enemy.definition.key in {"sewer_rat", "small_imp"} and step == "defeat_vermin":
                self.database.grant_flag(self.character.id, "human_combat_training_complete")
                self.database.complete_quest(self.character.id, HUMAN_COMBAT_TRAINING.key)
                await self.send("Quest complete: Lessons Beyond the Gate.\r\n")

        mobile_key = self.active_mobile_npc_key
        if mobile_key and self.mobile_npcs is not None:
            self.mobile_npcs.defeat(mobile_key)
            await self._stop_combat(disengage_mobile_npc=False)
        else:
            await self._stop_combat()
        await self.send_client_state()

    async def _combat_loop(self, enemy: EnemyState) -> None:
        assert self.character is not None and self.combatant is not None
        loop = asyncio.get_running_loop()
        next_enemy_attack = loop.time() + enemy.definition.auto_attack_interval
        try:
            while self.state is SessionState.PLAYING and self.active_enemy is enemy and enemy.alive:
                now = loop.time()
                if self.combatant.auto_attack_ready(now):
                    self.combatant.consume_auto_attack(now)
                    attack_roll = random.randint(1, 20)
                    if attack_roll >= enemy.definition.armor_class:
                        damage = self.combatant.auto_attack_damage(2)
                        dealt = enemy.take_damage(damage)
                        await self.send(
                            f"\r\nYou strike {enemy.definition.name} for {dealt} damage "
                            f"({enemy.current_hp}/{enemy.definition.max_hp} HP).\r\n"
                        )
                        await self.send_client_state()
                        if not enemy.alive:
                            await self._finish_enemy_defeat(enemy)
                            return
                    else:
                        await self.send(f"\r\nYour attack misses {enemy.definition.name}.\r\n")

                if enemy.definition.retaliates and now >= next_enemy_attack and enemy.alive:
                    damage = enemy.definition.auto_attack_damage
                    if now < self.ward_until:
                        damage = max(1, damage // 2)
                    self.combatant.current_hp = max(0, self.combatant.current_hp - damage)
                    await self.send(
                        f"\r\n{enemy.definition.name} hits you for {damage} damage "
                        f"({self.combatant.current_hp}/{self.combatant.max_hp} HP).\r\n"
                    )
                    await self.send_client_state()
                    next_enemy_attack = now + enemy.definition.auto_attack_interval
                    if self.combatant.current_hp <= 0:
                        if enemy.definition.tutorial:
                            recovery_room = HUMAN_TRAINING_YARD_KEY
                            await self.send(
                                "\r\nA training guard drags you clear before the creature can finish the job. "
                                "You recover in the Training Yard.\r\n"
                            )
                        else:
                            await self._handle_character_death(enemy.definition.name)
                            return
                        self.combatant.current_hp = self.combatant.max_hp
                        self.combatant.current_mana = self.combatant.max_mana
                        self.database.set_character_room(self.character.id, recovery_room)
                        refreshed = self.database.get_character_by_name(self.character.name)
                        if refreshed is not None:
                            self.character = refreshed
                        await self._stop_combat()
                        return
                await asyncio.sleep(0.15)
        except asyncio.CancelledError:
            return

    def _enemy_in_current_room(self, target_text: str) -> EnemyState | None:
        assert self.character is not None
        room = ROOMS_BY_KEY.get(self.character.current_room or "")
        if room is None:
            return None
        for enemy_key in room.enemy_keys:
            definition = ENEMIES_BY_KEY.get(enemy_key)
            if definition and definition.matches(target_text):
                return EnemyState(definition)
        return None

    async def start_combat(self, target_text: str) -> None:
        assert self.character is not None and self.combatant is not None
        if self.active_enemy is not None:
            await self.send(f"You are already fighting {self.active_enemy.definition.name}.\r\n")
            return
        enemy = self._enemy_in_current_room(target_text)
        if enemy is not None:
            self.active_enemy = enemy
            self.active_mobile_npc_key = None
            self.combatant.next_auto_attack_at = asyncio.get_running_loop().time()
            enemy.hate.add_threat(self.character.id, 1.0)
            await self.send(
                f"You engage {enemy.definition.name}. Your normal weapon attacks will now repeat automatically.\r\n"
            )
            await self.send_client_state()
            self.combat_task = asyncio.create_task(self._combat_loop(enemy))
            return

        mobile_state = self._mobile_npc_in_current_room(target_text)
        if mobile_state is not None and mobile_state.definition.aggressive:
            if await self.start_mobile_npc_combat(mobile_state.definition.key):
                return
        await self.send("You do not see an attackable target by that name here.\r\n")

    def _mobile_npc_in_current_room(self, target_text: str):
        if self.character is None or self.mobile_npcs is None:
            return None
        normalized = target_text.strip().lower()
        for state in self.mobile_npcs.npcs_in_room(self.character.current_room or ""):
            definition = state.definition
            names = {definition.name.lower(), *(alias.lower() for alias in definition.aliases)}
            if normalized in names:
                return state
        return None

    @staticmethod
    def _enemy_from_mobile_npc(state) -> EnemyState:
        definition = state.definition
        return EnemyState(
            EnemyDefinition(
                key=definition.key,
                name=definition.name,
                aliases=definition.aliases,
                description=definition.short_description,
                max_hp=definition.max_hp,
                armor_class=definition.armor_class,
                auto_attack_damage=definition.auto_attack_damage,
                auto_attack_interval=definition.auto_attack_interval,
                xp_reward=definition.xp_reward,
                retaliates=definition.aggressive,
                tutorial=False,
            )
        )

    async def start_mobile_npc_combat(self, npc_key: str, *, initiated_by_npc: bool = False) -> bool:
        assert self.character is not None and self.combatant is not None
        if self.mobile_npcs is None or self.active_enemy is not None:
            return False
        state = self.mobile_npcs.states.get(npc_key)
        if state is None or not state.active or state.current_room_key != self.character.current_room:
            return False
        if not self.mobile_npcs.engage(npc_key, self.character.id):
            return False

        enemy = self._enemy_from_mobile_npc(state)
        self.active_enemy = enemy
        self.active_mobile_npc_key = npc_key
        self.combatant.next_auto_attack_at = asyncio.get_running_loop().time()
        enemy.hate.add_threat(self.character.id, 1.0)
        if initiated_by_npc:
            await self.send(
                f"\r\n{enemy.definition.name} notices you at close range and lunges to attack!\r\n"
            )
        else:
            await self.send(
                f"You engage {enemy.definition.name}. Your normal weapon attacks will now repeat automatically.\r\n"
            )
        await self.send_client_state()
        self.combat_task = asyncio.create_task(self._combat_loop(enemy))
        return True

    async def check_mobile_npc_aggression(self, npc_key: str | None = None) -> bool:
        """Start combat only when an aggressive mobile NPC shares the room.

        This deliberately performs no adjacent-room scan. An NPC two rooms
        away cannot acquire the player simply because it is a hunter.
        """
        if (
            self.character is None
            or self.combatant is None
            or self.mobile_npcs is None
            or self.active_enemy is not None
            or self.state is not SessionState.PLAYING
        ):
            return False

        candidates = self.mobile_npcs.aggressive_npcs_in_room(self.character.current_room or "")
        for state in candidates:
            if npc_key is not None and state.definition.key != npc_key:
                continue
            if await self.start_mobile_npc_combat(state.definition.key, initiated_by_npc=True):
                return True
        return False

    def _available_flee_exits(self) -> list[tuple[str, str]]:
        assert self.character is not None
        room = ROOMS_BY_KEY.get(self.character.current_room or "")
        if room is None:
            return []
        exits = list(room.exits.items())
        if (
            room.key == SPOREKIN_FORGOTTEN_GROVE_ROOM_KEY
            and "sporekin_forgotten_pulse_solved" in self.database.list_flags(self.character.id)
        ):
            exits.append(("north", SPOREKIN_MEMORY_PATH_ROOM_KEY))
        return exits

    async def attempt_flee(self) -> None:
        assert self.character is not None
        if self.active_enemy is None:
            await self.send("You are not fighting anything.\r\n")
            return

        exits = self._available_flee_exits()
        if not exits:
            await self.send("There is nowhere to flee!\r\n")
            return

        enemy_name = self.active_enemy.definition.name
        if not FLEE_RULES.succeeds(random.random()):
            await self.send(f"You try to break away, but {enemy_name} cuts off your escape!\r\n")
            return

        direction, destination = random.choice(exits)
        mobile_key = self.active_mobile_npc_key
        movement: NpcMovement | None = None
        if mobile_key and self.mobile_npcs is not None:
            movement = self.mobile_npcs.attempt_pursuit_after_flee(
                mobile_key, self.character.id, destination, random.Random()
            )

        self.database.set_character_room(self.character.id, destination)
        refreshed = self.database.get_character_by_name(self.character.name)
        if refreshed is not None:
            self.character = refreshed
        await self.send(f"You break away and flee {direction}!\r\n\r\n")
        await self.show_current_room()

        if movement is not None:
            if self.mobile_npc_movement_callback is not None:
                await self.mobile_npc_movement_callback(movement)
            await self.send(
                f"{enemy_name} refuses to give up the chase and follows you {direction}!\r\n"
            )
            await self.send_client_state()
            return

        await self._stop_combat()
        await self.send_client_state()
        await self.send(f"You lose {enemy_name} and escape combat.\r\n")

    async def _apply_rot(self, enemy: EnemyState, damage_per_tick: int, ticks: int = 3, interval: float = 2.0) -> None:
        """Apply the Necromancer's first damage-over-time spell asynchronously.

        The effect remains intentionally small at this stage: three pulses over
        six seconds. It ends if combat ends or the target dies.
        """
        try:
            for pulse in range(1, ticks + 1):
                await asyncio.sleep(interval)
                if self.active_enemy is not enemy or not enemy.alive:
                    return
                dealt = enemy.take_damage(damage_per_tick)
                await self.send(
                    f"\r\nRot gnaws at {enemy.definition.name} for {dealt} damage "
                    f"({enemy.current_hp}/{enemy.definition.max_hp} HP).\r\n"
                )
                await self.send_client_state()
                if not enemy.alive:
                    await self._finish_enemy_defeat(enemy)
                    return
        except asyncio.CancelledError:
            return

    async def use_ability(self, ability_text: str) -> None:
        assert self.character is not None and self.combatant is not None
        abilities = class_abilities_for_level(
            self.character.character_class or "", self.character.level, self.character.deity_key
        )
        normalized = ability_text.strip().lower().replace("_", " ")
        ability = next(
            (a for a in abilities if normalized in {a.key.replace("_", " "), a.name.lower()}),
            None,
        )
        if ability is None:
            await self.send("You do not have an unlocked ability by that name. Type ABILITIES.\r\n")
            return

        # Small provisional costs/cooldowns make the tutorial playable. The class
        # identities are locked; these balance values are not.
        tuning = {
            "taunt": (10, 5.0),
            "coldfire_burst": (5, 4.0),
            "minor_heal": (4, 5.0),
            "forage": (0, 0.0),
            "restoring_light": (4, 4.0),
            "guardian_ward": (4, 8.0),
            "judgment_bolt": (5, 4.0),
            "minor_life_tap": (5, 4.0),
            "raise_skeleton": (0, 3.0),
            "rot": (6, 6.0),
        }
        mana_cost, cooldown = tuning.get(ability.key, (ability.mana_cost or 0, ability.cooldown_seconds or 3.0))
        if not self.combatant.ability_ready(ability.key):
            await self.send("That ability is still on cooldown.\r\n")
            return
        if not self.combatant.spend_mana(mana_cost):
            await self.send("You do not have enough mana.\r\n")
            return

        used = False
        if ability.key == "taunt":
            if self.active_enemy is None:
                await self.send("You need an enemy to taunt.\r\n")
                self.combatant.current_mana += mana_cost
                return
            success = self.active_enemy.hate.taunt(
                self.character.id, self.character.level, random.random()
            )
            await self.send(
                "You bellow a vicious challenge and seize the enemy's attention.\r\n"
                if success else
                "Your taunt fails to fully seize the enemy's attention.\r\n"
            )
            used = True
        elif ability.key in {"coldfire_burst", "judgment_bolt"}:
            if self.active_enemy is None:
                await self.send("You need an active enemy target for that spell.\r\n")
                self.combatant.current_mana += mana_cost
                return
            base = 7 if ability.key == "coldfire_burst" else 6
            damage = self.combatant.spell_damage(base)
            dealt = self.active_enemy.take_damage(damage)
            await self.send(f"{ability.name} hits {self.active_enemy.definition.name} for {dealt} damage.\r\n")
            used = True
            if not self.active_enemy.alive:
                enemy = self.active_enemy
                await self._finish_enemy_defeat(enemy)
        elif ability.key == "minor_life_tap":
            if self.active_enemy is None:
                await self.send("You need an active enemy target for Minor Life Tap.\r\n")
                self.combatant.current_mana += mana_cost
                return
            damage = self.combatant.spell_damage(4)
            dealt = self.active_enemy.take_damage(damage)
            before = self.combatant.current_hp
            self.combatant.current_hp = min(self.combatant.max_hp, self.combatant.current_hp + dealt)
            restored = self.combatant.current_hp - before
            await self.send(
                f"Minor Life Tap tears {dealt} life from {self.active_enemy.definition.name}; "
                f"you recover {restored} HP.\r\n"
            )
            used = True
            if not self.active_enemy.alive:
                enemy = self.active_enemy
                await self._finish_enemy_defeat(enemy)
        elif ability.key == "rot":
            if self.active_enemy is None:
                await self.send("You need an active enemy target for Rot.\r\n")
                self.combatant.current_mana += mana_cost
                return
            # Mind contributes to each pulse through spell_damage, but the base
            # remains intentionally small because Rot is the first DoT spell.
            damage_per_tick = max(1, self.combatant.spell_damage(2))
            enemy = self.active_enemy
            task = asyncio.create_task(self._apply_rot(enemy, damage_per_tick))
            self.dot_tasks.add(task)
            task.add_done_callback(self.dot_tasks.discard)
            await self.send(f"A gray-black rot settles into {enemy.definition.name}.\r\n")
            used = True
        elif ability.key in {"minor_heal", "restoring_light"}:
            base = 6 if ability.key == "minor_heal" else 8
            healing = self.combatant.healing_amount(base)
            before = self.combatant.current_hp
            self.combatant.current_hp = min(self.combatant.max_hp, self.combatant.current_hp + healing)
            await self.send(f"{ability.name} restores {self.combatant.current_hp - before} HP.\r\n")
            used = True
        elif ability.key == "guardian_ward":
            self.ward_until = asyncio.get_running_loop().time() + 10.0
            await self.send("A protective ward settles around you, softening incoming blows.\r\n")
            used = True
        elif ability.key == "raise_skeleton":
            success = self.database.summon_pet_with_catalyst(
                self.character.id, pet_key="skeleton", catalyst_item_key="bone_chips", catalyst_quantity=1
            )
            if not success:
                await self.send("You need Bone Chips in your inventory to raise a Skeleton.\r\n")
                self.combatant.current_mana += mana_cost
                return
            await self.send("Bone chips knit together at your feet. A Skeleton rises to serve you.\r\n")
            used = True
        elif ability.key == "forage":
            await self.send("You study the surroundings for useful natural materials. Nothing suitable grows in this training area.\r\n")
            used = True
        else:
            await self.send("That ability is authored, but its executable combat effect has not been tuned yet.\r\n")
            self.combatant.current_mana += mana_cost
            return

        if used:
            self.database.record_ability_use(self.character.id, ability.key)
            self.combatant.start_cooldown(ability.key, cooldown)
            await self.send_client_state()

    async def playing_prompt(self) -> None:
        assert self.character is not None
        await self.send_client_state()
        command = await self.prompt("\r\n> ")
        if command is None:
            self.state = SessionState.DISCONNECTED
            return

        verb = command.strip().lower()
        if verb in {"help", "?"}:
            await self.send(
                "Commands: LOOK, EXITS, NORTH/SOUTH/EAST/WEST, SCORE, STATS, HEALTH, LORE, PROGRESS/ABILITIES, "
                "ATTACK/KILL <target>, USE/CAST <ability>, FLEE, BIND, ACCESS, INVENTORY, READ, QUESTS, TALK, "
                "EXAMINE, TOUCH, LISTEN, "
                "TRADES, PROFESSIONS, RECIPES, CRAFT, MINE, HARVEST, HERBALISM, SHOP, MENU, QUIT\r\n"
                "Mining is node-based; actual nodes will be placed into rooms when the room world is authored. "
                "Blacksmithing recipes are already executable when the character is at a forge with materials.\r\n"
            )
            return

        if verb in {"look", "l"}:
            await self.send("\r\n")
            await self.show_current_room()
            return

        if verb in {"exits", "exit"}:
            room = ROOMS_BY_KEY.get(self.character.current_room or "")
            exits = list(room.exits.keys()) if room else []
            if (
                room
                and room.key == SPOREKIN_FORGOTTEN_GROVE_ROOM_KEY
                and "sporekin_forgotten_pulse_solved" in self.database.list_flags(self.character.id)
            ):
                exits.append("north")
            if exits:
                await self.send("Exits: " + ", ".join(exits) + "\r\n")
            else:
                await self.send("No authored exits are available here yet.\r\n")
            return

        direction_aliases = {"n": "north", "s": "south", "e": "east", "w": "west", "u": "up", "d": "down"}
        direction = direction_aliases.get(verb, verb)
        if direction in {"north", "south", "east", "west", "up", "down"}:
            await self.move_character(direction)
            return

        if verb in {"examine waystone", "look waystone", "examine stone marker", "look stone marker"}:
            room = ROOMS_BY_KEY.get(self.character.current_room or "")
            if room is None or room.key != FOREST_ELF_WAYSTONE_BEND_KEY:
                await self.send("There is no such waystone here to examine.\r\n")
                return
            await self.send(
                "\r\nMoss fills most of the carving, but beneath the leaf-and-circle emblem three shallow lines remain clear: "
                "a river bend, a still pool, and a single oak at the edge of thick woods. The marks are practical rather than mystical—a map taught by symbols.\r\n"
            )
            quest = self.database.get_quest(self.character.id, FOREST_ELF_FIRST_WALK.key)
            if quest and quest.get("status") == "active" and quest.get("current_step") == "study_waystone":
                self.database.advance_quest(self.character.id, FOREST_ELF_FIRST_WALK.key, "listen_pool")
                await self.send("Quest updated: The Old River Path. Continue east to the Listening Pool and LISTEN.\r\n")
            return

        if verb in {"examine mark", "look mark", "examine symbol", "look symbol", "examine occult mark", "look occult mark"}:
            room = ROOMS_BY_KEY.get(self.character.current_room or "")
            if room is None or room.key != HUMAN_BLACKGLASS_ARCH_KEY:
                await self.send("There is no such mark here to examine.\r\n")
                return
            await self.send(
                "\r\nFresh cuts score the soot near the base of the Blackglass Arch: three hooked strokes curl inward around a hollow circle. "
                "The hand that made it was hurried, but deliberate. Someone later tried to scrape it away. The shape is unmistakably related to the half-erased signs around Cathedral Square. "
                "This is not old decoration; someone is using it now.\r\n"
            )
            quest = self.database.get_quest(self.character.id, HUMAN_LOWER_WARDS_INVESTIGATION.key)
            if quest and quest.get("status") == "active" and quest.get("current_step") == "inspect_mark":
                self.database.advance_quest(self.character.id, HUMAN_LOWER_WARDS_INVESTIGATION.key, "find_informant")
                await self.send(
                    "Quest updated: Marks in the Ash. Someone in the Lower Wards may know what this symbol means.\r\n"
                )
            return

        if verb in {
            "examine mushrooms", "examine mushroom ring", "examine ring", "look mushrooms",
            "look mushroom ring", "look ring", "examine stone", "look stone"
        }:
            room = ROOMS_BY_KEY.get(self.character.current_room or "")
            if room is None or room.key != SPOREKIN_FORGOTTEN_GROVE_ROOM_KEY:
                await self.send("There is no such mushroom ring here to examine.\r\n")
                return
            await self.send(
                "\r\nThe four caps form a deliberate circle around the old black stone. Shallow channels in the stone link four spore-stained hollows. "
                "The oldest residue traces a path from BLUE to AMBER, then VIOLET, and finally IVORY. The pattern feels less like writing than remembered rhythm.\r\n"
                "Try TOUCH <color> MUSHROOM to reproduce it.\r\n"
            )
            quest = self.database.get_quest(self.character.id, SPOREKIN_FORGOTTEN_PULSE.key)
            if quest and quest.get("status") == "active" and quest.get("current_step") == "study_ring":
                self.database.advance_quest(self.character.id, SPOREKIN_FORGOTTEN_PULSE.key, "touch_blue")
                await self.send("Quest updated: The Forgotten Pulse.\r\n")
            return

        if verb in {"listen", "listen grove", "listen to grove", "listen pool", "listen to pool", "listen water"}:
            room = ROOMS_BY_KEY.get(self.character.current_room or "")
            if room and room.key == FOREST_ELF_LISTENING_POOL_KEY:
                await self.send(
                    "You stop moving. Beneath birdsong and the faint slide of water, the pool carries a second rhythm—so slight it could be current, root, or magic. "
                    "The longer you listen, the easier it becomes to tell where the tended forest ends. North, the sounds grow rougher and less familiar.\r\n"
                )
                quest = self.database.get_quest(self.character.id, FOREST_ELF_FIRST_WALK.key)
                if quest and quest.get("status") == "active" and quest.get("current_step") == "listen_pool":
                    self.database.advance_quest(self.character.id, FOREST_ELF_FIRST_WALK.key, "reach_outer_grove")
                    await self.send("Quest updated: The Old River Path. Follow the trail north to the Outer Grove.\r\n")
            elif room and room.key == SPOREKIN_FORGOTTEN_GROVE_ROOM_KEY:
                await self.send(
                    "The shared consciousness is distant here. Beneath the rain you sense only an old four-beat memory: cool blue, warm amber, dusk violet, pale ivory.\r\n"
                )
            else:
                await self.send("You listen, but hear nothing beyond the ordinary sounds around you.\r\n")
            return

        if verb.startswith("touch "):
            room = ROOMS_BY_KEY.get(self.character.current_room or "")
            if room is None or room.key != SPOREKIN_FORGOTTEN_GROVE_ROOM_KEY:
                await self.send("Nothing here responds to that touch.\r\n")
                return
            target = verb.split(maxsplit=1)[1].strip()
            color_aliases = {
                "blue": "blue", "blue mushroom": "blue", "blue cap": "blue",
                "amber": "amber", "amber mushroom": "amber", "amber cap": "amber",
                "violet": "violet", "violet mushroom": "violet", "violet cap": "violet",
                "ivory": "ivory", "ivory mushroom": "ivory", "ivory cap": "ivory",
                "white": "ivory", "white mushroom": "ivory", "pale mushroom": "ivory",
            }
            color = color_aliases.get(target)
            if color is None:
                await self.send("Touch which mushroom? The ring contains blue, amber, violet, and ivory caps.\r\n")
                return
            quest = self.database.get_quest(self.character.id, SPOREKIN_FORGOTTEN_PULSE.key)
            if quest is None or quest.get("status") != "active":
                if "sporekin_forgotten_pulse_solved" in self.database.list_flags(self.character.id):
                    await self.send(f"The {color} mushroom answers with a soft familiar glow, but the old pulse is already restored.\r\n")
                else:
                    await self.send("The mushroom glows beneath your fingers, but no larger pattern answers.\r\n")
                return
            step = quest.get("current_step")
            if step == "study_ring":
                await self.send("The cap glows, then fades without answer. You should EXAMINE RING before attempting the pattern.\r\n")
                return
            expected = {
                "touch_blue": "blue",
                "touch_amber": "amber",
                "touch_violet": "violet",
                "touch_ivory": "ivory",
            }
            next_step = {
                "touch_blue": "touch_amber",
                "touch_amber": "touch_violet",
                "touch_violet": "touch_ivory",
            }
            expected_color = expected.get(str(step))
            if expected_color is None:
                await self.send("The mushroom ring waits in silence.\r\n")
                return
            if color != expected_color:
                self.database.advance_quest(self.character.id, SPOREKIN_FORGOTTEN_PULSE.key, "touch_blue")
                await self.send(
                    f"The {color} cap flares sharply. For an instant every mushroom in the ring goes dark. A moment later the blue cap begins its slow pulse again. The sequence has reset.\r\n"
                )
                return
            await self.send(f"The {color} mushroom brightens beneath your hand. Its pulse passes into the ring.\r\n")
            if step in next_step:
                self.database.advance_quest(self.character.id, SPOREKIN_FORGOTTEN_PULSE.key, next_step[str(step)])
                return
            self.database.complete_quest(self.character.id, SPOREKIN_FORGOTTEN_PULSE.key)
            self.database.grant_flag(self.character.id, "sporekin_forgotten_pulse_solved")
            await self.send(
                "\r\nAll four mushrooms ignite together. The central stone exhales a cloud of silver spores that refuses to fall. "
                "For several breaths they hang in the air as a luminous spore-shaped sigil, then turn north. Roots loosen and reveal a narrow path that was invisible moments ago.\r\n"
                "\r\nQuest complete: The Forgotten Pulse. A new path is open to the north.\r\n"
            )
            return

        if verb in {"read note", "read cathedral note", "read sealed note", "read sealed cathedral note"}:
            if self.database.item_quantity(self.character.id, "sealed_cathedral_note") <= 0:
                await self.send("You are not carrying such a note.\r\n")
                return
            training = self.database.get_quest(self.character.id, HUMAN_COMBAT_TRAINING.key)
            if training and training.get("status") == "active":
                await self.send(
                    "\r\nThe original cathedral summons remains on the front. Across the reverse, in the High Acolyte's hand, is a newer instruction:\r\n\r\n"
                    "  Leave through the Demon Gate and follow the outer wall to the Training Yard.\r\n"
                    "  Begin in the Practice Ring. When the wood stops frightening you, enter the Vermin Pens.\r\n\r\n"
                    "A final line has been added beneath it: Do not mistake survival for mastery.\r\n"
                )
                if training.get("current_step") == "read_training_orders":
                    self.database.advance_quest(self.character.id, HUMAN_COMBAT_TRAINING.key, "reach_training_yard")
                    await self.send("Quest updated: Lessons Beyond the Gate.\r\n")
                return
            await self.send(
                "\r\nThe dark wax breaks with a dry crack. The message is brief:\r\n\r\n"
                "  Present yourself to the High Acolyte in the Grand Cathedral.\r\n"
                "  Come by the city streets. Learn the way.\r\n\r\n"
                "No signature follows, only the impressed seal of the cathedral clerical order.\r\n"
            )
            quest = self.database.get_quest(self.character.id, HUMAN_CATHEDRAL_SUMMONS.key)
            if quest and quest.get("status") == "active" and quest.get("current_step") == "read_note":
                self.database.advance_quest(self.character.id, HUMAN_CATHEDRAL_SUMMONS.key, "find_cathedral")
                await self.send("Quest updated: A Summons to the Cathedral.\r\n")
            return

        if verb.startswith("read "):
            await self.send("You cannot read that.\r\n")
            return

        if verb in {"quests", "quest", "journal"}:
            rows = self.database.list_quests(self.character.id)
            await self.send("\r\n--- Quest Journal ---\r\n")
            if not rows:
                await self.send("No quests.\r\n")
            for row in rows:
                definition = QUESTS_BY_KEY.get(str(row["quest_key"]))
                name = definition.name if definition else str(row["quest_key"])
                status = str(row["status"]).upper()
                await self.send(f"{name} [{status}]\r\n")
                if definition and row.get("status") == "active":
                    objective = definition.objective_for_step(row.get("current_step"))
                    if objective:
                        await self.send(f"  Objective: {objective}\r\n")
            return

        if verb in {"talk high acolyte", "talk to high acolyte", "talk acolyte", "talk to acolyte"}:
            room = ROOMS_BY_KEY.get(self.character.current_room or "")
            if room is None or "human_high_acolyte" not in room.npc_keys:
                await self.send("The High Acolyte is not here.\r\n")
                return
            npc = NPCS_BY_KEY["human_high_acolyte"]
            summons = self.database.get_quest(self.character.id, HUMAN_CATHEDRAL_SUMMONS.key)
            training = self.database.get_quest(self.character.id, HUMAN_COMBAT_TRAINING.key)
            lower = self.database.get_quest(self.character.id, HUMAN_LOWER_WARDS_INVESTIGATION.key)

            # Once the tutorial is complete, the High Acolyte becomes the handoff
            # into the first true Human-city investigation.
            if training and training.get("status") == "completed" and lower is None:
                await self.send(
                    "\r\nThe High Acolyte listens to the account of your training, then lets the silence linger.\r\n"
                    "'Good. You can survive a controlled fight. Now I need to know whether you can notice what a city is trying not to show you.'\r\n"
                    "'There have been whispers in the Lower Wards. Sealed passages marked, then scrubbed clean. People pretending not to have seen them.'\r\n"
                    "The Acolyte points toward the nave doors. 'Go west from Ashen Way and descend. Do not announce that the cathedral sent you. Find the mark first. Then find someone who knows why it is there.'\r\n"
                )
                self.database.start_quest(self.character.id, HUMAN_LOWER_WARDS_INVESTIGATION.key, "find_lower_wards")
                await self.send("\r\nNew quest: Marks in the Ash. Type QUESTS to review the investigation.\r\n")
                return

            if lower and lower.get("status") == "active":
                objective = HUMAN_LOWER_WARDS_INVESTIGATION.objective_for_step(lower.get("current_step"))
                await self.send(
                    "\r\nThe High Acolyte regards you with measured patience. 'The Lower Wards do not reward loud questions. Follow what you can prove.'\r\n"
                )
                if objective:
                    await self.send(f"Current objective: {objective}\r\n")
                return

            if lower and lower.get("status") == "completed":
                await self.send(
                    "\r\nThe High Acolyte's expression tightens at the mention of the old cistern tunnels. 'Then the whispers have roots. We will speak of what lies below when we know which doors are still locked.'\r\n"
                )
                return

            await self.send("\r\n")
            for line in npc.dialogue:
                await self.send(line + "\r\n")
            if summons and summons.get("status") == "active":
                if summons.get("current_step") == "read_note":
                    self.database.advance_quest(self.character.id, HUMAN_CATHEDRAL_SUMMONS.key, "find_cathedral")
                self.database.complete_quest(self.character.id, HUMAN_CATHEDRAL_SUMMONS.key)
                self.database.grant_flag(self.character.id, "met_high_acolyte")
                await self.send("\r\nQuest complete: A Summons to the Cathedral.\r\n")
            if training is None:
                if self.database.item_quantity(self.character.id, "sealed_cathedral_note") <= 0:
                    self.database.add_item(self.character.id, "sealed_cathedral_note", 1)
                self.database.start_quest(self.character.id, HUMAN_COMBAT_TRAINING.key, "read_training_orders")
                await self.send(
                    "New quest: Lessons Beyond the Gate. The High Acolyte has written new orders on the reverse of your note. Type READ NOTE.\r\n"
                )
            return

        if verb in {"talk informant", "talk to informant", "talk grey-cloaked informant", "talk to grey-cloaked informant", "talk grey cloaked informant", "talk to grey cloaked informant"}:
            room = ROOMS_BY_KEY.get(self.character.current_room or "")
            if room is None or "human_lower_wards_informant" not in room.npc_keys:
                await self.send("There is no informant here willing to speak with you.\r\n")
                return
            quest = self.database.get_quest(self.character.id, HUMAN_LOWER_WARDS_INVESTIGATION.key)
            npc = NPCS_BY_KEY["human_lower_wards_informant"]
            if not quest or quest.get("status") != "active" or quest.get("current_step") != "find_informant":
                await self.send(
                    "\r\nThe grey-cloaked local studies you without interest. 'If you want information, bring me a question worth answering.'\r\n"
                )
                return
            await self.send("\r\n")
            for line in npc.dialogue:
                await self.send(line + "\r\n")
            self.database.complete_quest(self.character.id, HUMAN_LOWER_WARDS_INVESTIGATION.key)
            self.database.grant_flag(self.character.id, "human_lower_wards_mark_traced")
            await self.send(
                "\r\nQuest complete: Marks in the Ash.\r\n"
                "You now know where the trail leads next: the old cistern tunnels beneath the Lower Wards.\r\n"
            )
            return

        if verb.startswith("talk"):
            await self.send("There is no one by that name here to speak with.\r\n")
            return

        if verb.startswith("attack ") or verb.startswith("kill "):
            target = command.strip().split(maxsplit=1)[1]
            await self.start_combat(target)
            return

        if verb in {"flee", "disengage"}:
            await self.attempt_flee()
            return

        if verb.startswith("use ") or verb.startswith("cast "):
            ability_text = command.strip().split(maxsplit=1)[1]
            await self.use_ability(ability_text)
            return

        # Dreams of the Fallen convenience: common level-one abilities can be typed directly.
        direct_abilities = {
            "taunt": "taunt",
            "coldfire": "coldfire burst",
            "coldfire burst": "coldfire burst",
            "minor heal": "minor heal",
            "forage": "forage",
            "restoring light": "restoring light",
            "guardian ward": "guardian ward",
            "judgment bolt": "judgment bolt",
            "raise skeleton": "raise skeleton",
        }
        if verb in direct_abilities:
            await self.use_ability(direct_abilities[verb])
            return

        if verb in {"health", "hp", "mana"}:
            if self.combatant is None:
                await self.send("Combat state is not initialized.\r\n")
            else:
                target = self.active_enemy
                await self.send(
                    f"HP: {self.combatant.current_hp}/{self.combatant.max_hp}  Mana: {self.combatant.current_mana}/{self.combatant.max_mana}  Movement: {self.combatant.current_movement}/{self.combatant.max_movement}\r\n"
                )
                if target is not None:
                    await self.send(f"Target: {target.definition.name} {target.current_hp}/{target.definition.max_hp} HP\r\n")
            return

        if verb in {"bind", "bindpoint", "bind point"}:
            bind_key = self.character.bind_room
            room = ROOMS_BY_KEY.get(bind_key or "")
            if room is None:
                await self.send("Your bind point has not been established yet.\r\n")
            else:
                await self.send(
                    f"Bind point: {room.name}. If you die, you will return here.\r\n"
                )
            return

        if verb in {"score", "status", "sheet", "stats"}:
            race = RACES_BY_KEY.get(self.character.race or "")
            character_class = CLASSES_BY_KEY.get(self.character.character_class or "")
            await self.send(
                f"\r\nName : {self.character.name}\r\n"
                f"Race : {race.name if race else self.character.race}\r\n"
                f"Class: {character_class.name if character_class else self.character.character_class}\r\n"
                + (
                    f"Deity: {PRIEST_DEITIES_BY_KEY.get(self.character.deity_key).name if self.character.deity_key in PRIEST_DEITIES_BY_KEY else (self.character.deity_key or 'not yet chosen')}\r\n"
                    if self.character.character_class == "priest"
                    else ""
                )
                + f"Level: {self.character.level}\r\n"
                f"XP   : {self.character.experience}\r\n"
                f"Next : {PROGRESSION_RULES.cumulative_xp_for_level(self.character.level + 1)} total XP\r\n"
                f"\r\n--- Stats ---\r\n"
                f"Might: {self.character.might}  (auto-attack damage)\r\n"
                f"Grace: {self.character.grace}  (auto-attack speed)\r\n"
                f"Love : {self.character.love}  (healing + mana)\r\n"
                f"Mind : {self.character.mind}  (spell damage + mana)\r\n"
                f"HP   : {self.character.hp_stat}  (raw max HP bonus)\r\n"
                f"AC   : 0  (equipment-derived; inventory/equipment system pending)\r\n"
                f"Mana bonus from stats: {self.character.love + self.character.mind}\r\n"
            )
            if race and race.passive_name:
                await self.send(f"Passive: {race.passive_name} - {race.passive_description}\r\n")
            return

        if verb == "lore":
            race = RACES_BY_KEY.get(self.character.race or "")
            if race:
                await self.send(f"\r\n--- {race.name} ---\r\n{race.description}\r\n")
                for item in race.lore:
                    await self.send(f"- {item}\r\n")
            return

        if verb in {"progress", "skills", "abilities"}:
            progress = self.database.list_ability_progress(self.character.id)
            class_key = self.character.character_class or ""
            fixed = (
                class_abilities_for_level(class_key, 10_000, self.character.deity_key)
                if class_key == "priest"
                else FIXED_CLASS_ABILITIES.get(class_key, ())
            )
            unlocked = {
                ability.key
                for ability in class_abilities_for_level(
                    class_key, self.character.level, self.character.deity_key
                )
            }
            await self.send("\r\n--- Ability Progress ---\r\n")
            await self.send("Class ability sets are fixed; players do not choose from a talent pool.\r\n")
            if fixed:
                await self.send("Class abilities:\r\n")
                for ability in fixed:
                    level_text = "?" if ability.unlock_level is None else str(ability.unlock_level)
                    status = "UNLOCKED" if ability.key in unlocked else f"LOCKED (level {level_text})"
                    await self.send(f"- {ability.name}: {status} - {ability.description}\r\n")
            elif class_key == "priest":
                await self.send(
                    "Priest abilities branch from the chosen deity. This Priest does not yet have a valid deity path.\r\n"
                )
            else:
                await self.send("This class's authored ability list has not been designed yet.\r\n")
            if not progress:
                await self.send("No practiced abilities yet. Abilities gain skill progression through use.\r\n")
            else:
                for item in progress:
                    await self.send(
                        f"{item['ability_key']}: {item['uses']} uses, {item['skill_xp']} skill XP\r\n"
                    )
            return

        if verb in {"access", "flags", "keys"}:
            flags = sorted(self.database.list_flags(self.character.id))
            keys = sorted(self.database.list_keys(self.character.id))
            await self.send("\r\n--- Character Access ---\r\n")
            await self.send("Flags: " + (", ".join(flags) if flags else "none") + "\r\n")
            await self.send("Keys : " + (", ".join(keys) if keys else "none") + "\r\n")
            await self.send("Astralis is mostly open; authored areas may require these keys/flags or a group.\r\n")
            return

        if verb in {"shop", "list", "wares"}:
            if self.mobile_npcs is None:
                await self.send("There is no merchant here.\r\n")
                return
            merchants_here = []
            for state in self.mobile_npcs.npcs_in_room(self.character.current_room or ""):
                merchant = MERCHANTS_BY_NPC_KEY.get(state.definition.key)
                if merchant is not None:
                    merchants_here.append((state.definition, merchant))
            if not merchants_here:
                await self.send("There is no merchant here.\r\n")
                return
            definition, merchant = merchants_here[0]
            await self.send(f"\r\n--- {definition.name}'s Wares ---\r\n")
            for stock in merchant.stock:
                item = ITEMS_BY_KEY.get(stock.item_key)
                name = item.name if item else stock.item_key
                await self.send(f"{name}\r\n")
            await self.send(
                "Bone Chips are common merchant stock. Prices will be attached when Astralis's currency system is finalized.\r\n"
            )
            return

        if verb in {"inventory", "inv", "i"}:
            items = self.database.list_items(self.character.id)
            await self.send("\r\n--- Inventory ---\r\n")
            if not items:
                await self.send("Empty.\r\n")
            else:
                for row in items:
                    definition = ITEMS_BY_KEY.get(str(row["item_key"]))
                    name = definition.name if definition else str(row["item_key"])
                    await self.send(f"{int(row['quantity'])}x {name}\r\n")
            return

        if verb in {"professions", "crafting"}:
            await self.send("\r\n--- Crafting Professions ---\r\n")
            for profession in PROFESSIONS:
                await self.send(f"{profession.name}: {profession.description}\r\n")
            await self.send("\r\nGathering:\r\n")
            for skill in GATHERING_SKILLS:
                suffix = " (node-based)" if skill.node_based else ""
                await self.send(f"{skill.name}{suffix}: {skill.description}\r\n")
            return

        if verb in {"trades", "trade", "craftskills"}:
            skills = self.database.list_trade_skills(self.character.id)
            await self.send("\r\n--- Trade & Gathering Skills ---\r\n")
            if not skills:
                await self.send("No practiced trade skills yet.\r\n")
            else:
                for row in skills:
                    await self.send(
                        f"{row['trade_skill_key']}: {row['uses']} uses, {row['skill_xp']} skill XP\r\n"
                    )
            return

        if verb.startswith("recipes"):
            await self.send("\r\n--- Crafting Recipes ---\r\n")
            authored_recipe_professions = tuple(
                profession.key
                for profession in PROFESSIONS
                if any(recipe.trade_skill_key == profession.key for recipe in ALL_RECIPES)
            )
            for profession in authored_recipe_professions:
                await self.send(f"\r\n{profession.title()}:\r\n")
                for recipe in (r for r in ALL_RECIPES if r.trade_skill_key == profession):
                    materials = ", ".join(
                        f"{requirement.quantity}x {ITEMS_BY_KEY.get(requirement.item_key).name if requirement.item_key in ITEMS_BY_KEY else requirement.item_key}"
                        for requirement in recipe.materials
                    )
                    output = ITEMS_BY_KEY.get(recipe.output_item_key)
                    output_name = output.name if output else recipe.output_item_key
                    await self.send(
                        f"{recipe.key}: {output_name} | skill {recipe.minimum_skill} | {materials} | station: {recipe.station_key or 'none'}\r\n"
                    )
            await self.send("\r\nBlacksmithing: Iron -> Steel -> Cobalt -> Moonsteel -> Emberite -> Stariron -> Astralite.\r\n")
            await self.send("Tailoring: Cotton -> Wool -> Silk -> Moonweave -> Spidersilk -> Ghostweave -> Astralweave.\r\n")
            await self.send("Alchemy begins with herbs and branches into potions, antidotes, tinctures, essential oils, and perfumes.\r\n")
            await self.send("Recipe skill thresholds, material quantities, item stats, and consumable effects are provisional tuning.\r\n")
            return

        if verb.startswith("craft "):
            recipe_key = verb.split(maxsplit=1)[1].strip().replace(" ", "_")
            # The playable shell has no authored rooms/stations yet, so there is
            # deliberately no invisible forge available everywhere.
            result = craft_recipe(self.database, self.character.id, recipe_key, station_key=None)
            await self.send(result.message + "\r\n")
            return

        if verb in {"mine", "mining"}:
            await self.send(
                "Mining is node-based. No resource node exists in this temporary playable shell; "
                "ore veins and other mining nodes will be placed in authored rooms and mined from the node itself.\r\n"
            )
            return

        if verb in {"harvest", "gather", "harvesting"}:
            await self.send(
                "Harvesting is node-based. Cotton patches and other fiber-resource nodes will be placed in authored rooms; "
                "gathering them improves Harvesting through use. Herbal ingredients use the separate Herbalism skill.\r\n"
            )
            return

        if verb in {"herbalism", "herbs"}:
            await self.send(
                "Herbalism is node-based. Greenleaf, Bitterroot, Lavender, and later alchemical plants will be placed in authored rooms; "
                "gathering herb nodes yields ingredients for Alchemy and improves Herbalism through use.\r\n"
            )
            return

        if verb in {"menu", "characters"}:
            await self._stop_combat()
            self.character = None
            self.combatant = None
            self.state = SessionState.CHARACTER_MENU
            return

        if verb in {"quit", "q"}:
            await self._stop_combat()
            await self.send("\r\nGoodbye.\r\n")
            self.state = SessionState.DISCONNECTED
            return

        await self.send("Unknown command. Type HELP.\r\n")

    async def character_creation_flow(self) -> None:
        """Create a character in the agreed race -> class -> name order."""
        assert self.account is not None

        if not RACES:
            await self.send(
                "\r\nCharacter creation is ready for race selection, but no races "
                "have been defined yet.\r\n"
            )
            return

        race = await self.choose_creation_option("race", RACES)
        if race is None:
            return

        if not CLASSES:
            await self.send(
                "\r\nRace selected. Classes are the next part we need to define.\r\n"
            )
            return

        character_class = await self.choose_creation_option("class", CLASSES)
        if character_class is None:
            return

        deity_key: str | None = None
        if character_class.requires_deity_path:
            deity = await self.choose_priest_deity()
            if deity is None:
                return
            deity_key = deity.key

        allocated_stats = await self.allocate_creation_stats(race.key, character_class.key)
        if allocated_stats is None:
            return
        final_stats = build_starting_stats(race.key, character_class.key, allocated_stats)

        # Name rules are intentionally kept lightweight for now. We will make
        # the final naming policy a separate design decision before launch.
        while True:
            name = await self.prompt(
                "\r\nChoose your character's name (or type CANCEL): "
            )
            if name is None:
                self.state = SessionState.DISCONNECTED
                return
            if name.lower() == "cancel":
                await self.send("\r\nCharacter creation cancelled.\r\n")
                return
            if not re.fullmatch(r"[A-Za-z][A-Za-z'-]{1,19}", name):
                await self.send(
                    "Names must be 2-20 characters, begin with a letter, and "
                    "contain only letters, apostrophes, or hyphens.\r\n"
                )
                continue
            if self.database.get_character_by_name(name) is not None:
                await self.send("That character name is already taken.\r\n")
                continue
            break

        await self.send(
            "\r\n--- Character Summary ---\r\n"
            f"Race : {race.name}\r\n"
            f"Class: {character_class.name}\r\n"
            + (
                f"Deity: {PRIEST_DEITIES_BY_KEY[deity_key].name}\r\n"
                if deity_key else ""
            )
            + f"Name : {name}\r\n"
            f"Stats: Might {final_stats.might}, Grace {final_stats.grace}, Love {final_stats.love}, "
            f"Mind {final_stats.mind}, HP {final_stats.hp}\r\n"
        )
        confirm = await self.prompt("Create this character? (Y/N): ")
        if confirm is None:
            self.state = SessionState.DISCONNECTED
            return
        if confirm.lower() not in {"y", "yes"}:
            await self.send("\r\nCharacter creation cancelled.\r\n")
            return

        try:
            character = self.database.create_character(
                account_id=self.account.id,
                name=name,
                race=race.key,
                character_class=character_class.key,
                stats=final_stats,
                deity_key=deity_key,
            )
        except CharacterSlotLimitReached:
            await self.send(
                f"\r\nAll {MAX_CHARACTERS_PER_ACCOUNT} character slots are already in use.\r\n"
            )
            return
        except Exception:
            # Most commonly this means another player/session claimed the same
            # globally unique character name between our check and INSERT.
            await self.send(
                "\r\nThat character could not be created. The name may have just "
                "become unavailable.\r\n"
            )
            return

        await self.send(
            f"\r\n{character.name} has been created.\r\n"
        )

    async def choose_priest_deity(self):
        await self.send("\r\n--- Choose Your Deity ---\r\n")
        for index, deity in enumerate(PRIEST_DEITIES, start=1):
            await self.send(
                f"{index}) {deity.name} - {deity.domain.title()}\r\n"
                f"   {deity.description}\r\n"
                f"   Level 1: {deity.starter_ability.name} - {deity.starter_ability.description}\r\n"
            )
        await self.send("0) Cancel character creation\r\n")

        while True:
            choice = await self.prompt("\r\nDeity: ")
            if choice is None:
                self.state = SessionState.DISCONNECTED
                return None
            if choice in {"0"} or choice.lower() in {"cancel", "quit", "q"}:
                await self.send("\r\nCharacter creation cancelled.\r\n")
                return None
            if choice.isdigit() and 1 <= int(choice) <= len(PRIEST_DEITIES):
                return PRIEST_DEITIES[int(choice) - 1]
            await self.send("Invalid selection.\r\n")

    async def allocate_creation_stats(
        self, race_key: str, class_key: str
    ) -> CharacterStats | None:
        baseline = starting_stat_baseline(race_key, class_key)
        allocation = CharacterStats()
        remaining = STARTING_STAT_RULES.discretionary_points

        await self.send(
            "\r\n--- Allocate Starting Stats ---\r\n"
            "Race and class establish your baseline. You then spend discretionary points.\r\n"
            f"Baseline: Might {baseline.might}, Grace {baseline.grace}, Love {baseline.love}, "
            f"Mind {baseline.mind}, HP {baseline.hp}\r\n"
            f"Points to spend: {remaining}\r\n"
            "Use commands like MIGHT 2 or LOVE 1. Type RESET or CANCEL.\r\n"
        )

        while remaining > 0:
            answer = await self.prompt(f"Points remaining ({remaining}): ")
            if answer is None:
                self.state = SessionState.DISCONNECTED
                return None
            lowered = answer.lower().strip()
            if lowered in {"cancel", "q", "quit"}:
                await self.send("\r\nCharacter creation cancelled.\r\n")
                return None
            if lowered == "reset":
                allocation = CharacterStats()
                remaining = STARTING_STAT_RULES.discretionary_points
                await self.send("Stat allocation reset.\r\n")
                continue

            parts = lowered.split()
            if len(parts) != 2 or parts[0] not in STAT_KEYS or not parts[1].isdigit():
                await self.send("Enter a stat and amount, for example: MIGHT 2\r\n")
                continue
            amount = int(parts[1])
            if amount <= 0 or amount > remaining:
                await self.send(f"Choose an amount from 1 to {remaining}.\r\n")
                continue
            allocation = allocation.with_added_point(parts[0], amount)
            remaining -= amount
            current = baseline.plus(allocation)
            await self.send(
                f"Current: Might {current.might}, Grace {current.grace}, Love {current.love}, "
                f"Mind {current.mind}, HP {current.hp}\r\n"
            )

        return allocation

    async def choose_creation_option(
        self,
        label: str,
        options: tuple[RaceDefinition, ...] | tuple[ClassDefinition, ...],
    ) -> RaceDefinition | ClassDefinition | None:
        await self.send(f"\r\n--- Choose Your {label.title()} ---\r\n")
        for index, option in enumerate(options, start=1):
            await self.send(f"{index}) {option.name} - {option.description}\r\n")
            if isinstance(option, RaceDefinition) and option.passive_name:
                await self.send(
                    f"   Passive: {option.passive_name} - {option.passive_description}\r\n"
                )
        await self.send("0) Cancel character creation\r\n")

        while True:
            choice = await self.prompt(f"\r\n{label.title()}: ")
            if choice is None:
                self.state = SessionState.DISCONNECTED
                return None
            if choice in {"0"} or choice.lower() in {"cancel", "quit", "q"}:
                await self.send("\r\nCharacter creation cancelled.\r\n")
                return None
            if choice.isdigit() and 1 <= int(choice) <= len(options):
                return options[int(choice) - 1]
            await self.send("Invalid selection.\r\n")

    async def close(self) -> None:
        await self._stop_combat()
        if self.writer.is_closing():
            return
        self.writer.close()
        try:
            await self.writer.wait_closed()
        except ConnectionError:
            pass
