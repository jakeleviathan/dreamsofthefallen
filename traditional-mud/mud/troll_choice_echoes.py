from __future__ import annotations

from dataclasses import replace

import mud.crafting as crafting
import mud.troll_start as troll_start
import mud.world as legacy_world
from mud.crafting import ConsumableEffect, ItemDefinition
from mud.world import NpcDefinition, RoomDefinition
from mud import troll_survivor_choice as survivor


TROLL_SCOUT_ECHO_HEARD_FLAG = "troll_first_duty_scout_echo_heard"
TROLL_TRAIL_MARKER_GIFT_FLAG = "troll_first_duty_trail_marker_received"
TROLL_TRAIL_MARKER_USED_FLAG = "troll_first_duty_trail_marker_used"
TROLL_HEARTH_ECHO_HEARD_FLAG = "troll_first_duty_hearth_echo_heard"
TROLL_RATION_GIFT_FLAG = "troll_first_duty_ration_received"
TROLL_RATION_USED_FLAG = "troll_first_duty_ration_used"
TROLL_BRANNIK_CHOICE_ECHO_FLAG = "troll_first_duty_brannik_echo_heard"
TROLL_TRAIL_MARKER_ROOM_PREFIX = "troll_first_duty_marker_room:"

TROLL_TRAIL_MARKER_KEY = "frostroot_waxed_trail_marker"
TROLL_RATION_KEY = "frostroot_smoked_root_ration"

HARKA_PINE_EYE_KEY = "troll_scout_harka_pine_eye"
ODA_WARMSTONE_KEY = "troll_hearthkeeper_oda_warmstone"


WAXED_TRAIL_MARKER = ItemDefinition(
    key=TROLL_TRAIL_MARKER_KEY,
    name="Waxed Trail Marker",
    description=(
        "A thumb-long strip of pale hide rubbed with dark spruce wax. Scout Harka cut a notch "
        "into one end so it can be tied to a branch with the point facing along a chosen return "
        "route. It is deliberately simple, weather-resistant, and meant to be used once."
    ),
    category="utility",
    tier=0,
)

SMOKED_ROOT_RATION = ItemDefinition(
    key=TROLL_RATION_KEY,
    name="Smoked Root Ration",
    description=(
        "A compact packet of smoked winter root, rendered fat, and coarse salt wrapped in dry "
        "leaf and hide. Hearthkeeper Oda packed it for someone who might need food before they "
        "have time for a proper meal."
    ),
    category="consumable",
    consumable=ConsumableEffect(
        use_mode="eat",
        heal_hp=4,
        effect_tags=("food", "troll_first_duty_echo", "one_use"),
    ),
    tier=0,
)


HARKA_PINE_EYE = NpcDefinition(
    key=HARKA_PINE_EYE_KEY,
    name="Scout Harka Pine-Eye",
    short_description=(
        "a lean Troll scout sorting snapped twigs, hair, and scraps of cloth into separate "
        "pouches beside the trackline"
    ),
    room_key=troll_start.TROLL_TRACKLINE_VERGE_KEY,
    role="Frostroot scout and later social echo of the player's first post-raid duty",
    dialogue=(
        "Harka rolls a twig between two fingers. 'A track is only useful if you know what changed it after it was made.'",
        "'Wind erases. Snow fills. People lie. The ground does not promise to make any of that easy for you.'",
    ),
)

ODA_WARMSTONE = NpcDefinition(
    key=ODA_WARMSTONE_KEY,
    name="Hearthkeeper Oda Warmstone",
    short_description=(
        "an older Troll hearthkeeper checking covered coals with the back of one scarred hand "
        "before moving them between stone hearths"
    ),
    room_key=troll_start.TROLL_EMBER_HOLLOW_KEY,
    role="Frostroot hearthkeeper and later social echo of the player's first post-raid duty",
    dialogue=(
        "Oda nudges ash over a bright coal. 'A fire that lasts is worth more than a fire that looks impressive.'",
        "'Food, dry bedding, heat. People notice those things most when someone forgot them.'",
    ),
)


# First direction on a safe return toward Frostroot from nearby authored Troll rooms.
TRAIL_HOME_HINTS: dict[str, tuple[str, str]] = {
    troll_start.TROLL_HIDEWIND_RING_KEY: ("WEST", "Frostroot Camp"),
    troll_start.TROLL_EMBER_HOLLOW_KEY: ("SOUTH", "Frostroot Camp"),
    troll_start.TROLL_TRACKLINE_VERGE_KEY: ("WEST", "Ember Hollow, then south to Frostroot"),
    troll_start.TROLL_WHITEHORN_HOLLOW_KEY: ("WEST", "Trackline Verge"),
    troll_start.TROLL_TETHER_YARD_KEY: ("EAST", "Frostroot Camp"),
    troll_start.TROLL_WINDSCAR_SHELF_KEY: ("WEST", "Tether Yard, then east to Frostroot"),
    troll_start.TROLL_STONEJAW_PASS_KEY: ("SOUTH", "Ember Hollow, then south to Frostroot"),
    survivor.TROLL_BREACH_YARD_KEY: ("NORTH", "Frostroot Camp"),
    survivor.TROLL_SMOLDERING_TRAIL_KEY: ("NORTH", "South Breach Yard"),
    survivor.TROLL_CHURNED_GULLY_KEY: ("NORTH", "Smoldering Trail"),
    survivor.TROLL_ASHEN_SHELTER_ROW_KEY: ("EAST", "South Breach Yard, then north to Frostroot"),
}


def _replace_npc(npc: NpcDefinition) -> None:
    if npc.key in legacy_world.NPCS_BY_KEY:
        legacy_world.NPCS = tuple(
            npc if existing.key == npc.key else existing for existing in legacy_world.NPCS
        )
    else:
        legacy_world.NPCS = legacy_world.NPCS + (npc,)
    legacy_world.NPCS_BY_KEY[npc.key] = npc


def _room_with_npc(room_key: str, npc_key: str) -> RoomDefinition:
    original = legacy_world.ROOMS_BY_KEY[room_key]
    npc_keys = tuple(dict.fromkeys(original.npc_keys + (npc_key,)))
    return replace(original, npc_keys=npc_keys)


def _replace_room(room: RoomDefinition) -> None:
    legacy_world.ROOMS = tuple(
        room if existing.key == room.key else existing for existing in legacy_world.ROOMS
    )
    legacy_world.ROOMS_BY_KEY[room.key] = room


def install_troll_choice_echo_content(world_service=None) -> None:
    """Register small persistent social/mechanical echoes of the first Troll duty choice."""
    for item in (WAXED_TRAIL_MARKER, SMOKED_ROOT_RATION):
        if item.key not in crafting.ITEMS_BY_KEY:
            crafting.ITEMS = crafting.ITEMS + (item,)
        crafting.ITEMS_BY_KEY[item.key] = item

    for npc in (HARKA_PINE_EYE, ODA_WARMSTONE):
        _replace_npc(npc)

    trackline = _room_with_npc(troll_start.TROLL_TRACKLINE_VERGE_KEY, HARKA_PINE_EYE.key)
    ember = _room_with_npc(troll_start.TROLL_EMBER_HOLLOW_KEY, ODA_WARMSTONE.key)
    _replace_room(trackline)
    _replace_room(ember)

    if world_service is not None:
        world_service.legacy_rooms[trackline.key] = trackline
        world_service.legacy_rooms[ember.key] = ember
        cache = getattr(world_service, "_scene_cache", None)
        if cache is not None:
            cache.pop(trackline.key, None)
            cache.pop(ember.key, None)


def _flags(session) -> set[str]:
    if session.character is None:
        return set()
    return set(session.database.list_flags(session.character.id))


def _route_completed(session, route_flag: str) -> bool:
    return session.character is not None and route_flag in _flags(session)


def _gift_item_once(session, item_key: str, gift_flag: str) -> bool:
    assert session.character is not None
    flags = _flags(session)
    if gift_flag in flags:
        return False
    if session.database.item_quantity(session.character.id, item_key) <= 0:
        session.database.add_item(session.character.id, item_key, 1)
    session.database.grant_flag(session.character.id, gift_flag)
    return True


async def _talk_harka(session) -> bool:
    if (
        session.character is None
        or session.character.race != "troll"
        or session.character.current_room != troll_start.TROLL_TRACKLINE_VERGE_KEY
    ):
        return False

    flags = _flags(session)
    if survivor.TROLL_TRACK_ROUTE_COMPLETE_FLAG in flags:
        first_gift = _gift_item_once(session, TROLL_TRAIL_MARKER_KEY, TROLL_TRAIL_MARKER_GIFT_FLAG)
        session.database.grant_flag(session.character.id, TROLL_SCOUT_ECHO_HEARD_FLAG)
        if first_gift:
            await session.send(
                "\r\nHarka studies you for a moment before looking back at the ground. 'Raska kept the black-waxed cord you brought home. More important, he said you stopped chasing once you had facts worth returning with.'\r\n"
                "She takes a thumb-long strip of pale hide from a pouch and rubs spruce wax into it. One end has been cut into a sharp little point.\r\n"
                "'You already know how to read a trail. Learn to leave one useful thing for yourself, too. A marker is not an admission that you're lost. It is insurance against weather.'\r\n"
                "Harka gives you a Waxed Trail Marker. In nearby Troll country, use MARK TRAIL when you want one persistent reminder of the first safe direction back toward Frostroot.\r\n"
            )
        else:
            await session.send(
                "\r\nHarka glances at your hands. 'Read the whole trail, and remember the return before you need it. That lesson does not expire because you learned it once.'\r\n"
            )
        return True

    if survivor.TROLL_CAMP_ROUTE_COMPLETE_FLAG in flags:
        session.database.grant_flag(session.character.id, TROLL_SCOUT_ECHO_HEARD_FLAG)
        await session.send(
            "\r\nHarka gives you a short nod. 'I heard you stayed with the shelter row while half the camp was staring through the breach. Good.'\r\n"
            "She tucks a scrap of cloth into a sign pouch. 'Every scout needs somewhere dry to return to. The person who keeps that place standing is part of the trail whether they ever follow a track or not.'\r\n"
        )
        return True

    await session.send(
        "\r\nHarka sorts a bent twig from an unbroken one. 'When Raska has given you enough field work to know why that difference matters, come talk to me again.'\r\n"
    )
    return True


async def _talk_oda(session) -> bool:
    if (
        session.character is None
        or session.character.race != "troll"
        or session.character.current_room != troll_start.TROLL_EMBER_HOLLOW_KEY
    ):
        return False

    flags = _flags(session)
    if survivor.TROLL_CAMP_ROUTE_COMPLETE_FLAG in flags:
        first_gift = _gift_item_once(session, TROLL_RATION_KEY, TROLL_RATION_GIFT_FLAG)
        session.database.grant_flag(session.character.id, TROLL_HEARTH_ECHO_HEARD_FLAG)
        if first_gift:
            await session.send(
                "\r\nOda recognizes you before you introduce yourself. 'You're the one who pulled the sealed food out of the meltwater and closed that roof seam.'\r\n"
                "She presses a flat hide-wrapped packet into your palm. 'That saved more than a few meals. Take one back.'\r\n"
                "You receive a Smoked Root Ration. EAT SMOKED ROOT RATION when you are injured to restore 4 HP. It is a one-use field ration, not a permanent bonus.\r\n"
            )
        else:
            await session.send(
                "\r\nOda checks the ember pot, then gives you the same small nod she gives a roof that held through the night. 'Quiet work still counts after everyone stops talking about the raid.'\r\n"
            )
        return True

    if survivor.TROLL_TRACK_ROUTE_COMPLETE_FLAG in flags:
        session.database.grant_flag(session.character.id, TROLL_HEARTH_ECHO_HEARD_FLAG)
        await session.send(
            "\r\nOda glances toward Frostroot. 'Raska hung your signal cord where people can see it. Information brought home keeps fires lit too.'\r\n"
            "She covers a bright coal with ash. 'Just remember that every trail worth following should end somewhere people are still alive to hear what you found.'\r\n"
        )
        return True

    await session.send(
        "\r\nOda nudges the ember bed flatter. 'If you're here to learn fire, start by learning that keeping heat is usually more useful than making more flame.'\r\n"
    )
    return True


def _marker_room_flag(room_key: str) -> str:
    return TROLL_TRAIL_MARKER_ROOM_PREFIX + room_key


def _current_marker_hint(session) -> tuple[str, str] | None:
    if session.character is None:
        return None
    flags = _flags(session)
    room_key = session.character.current_room or ""
    if _marker_room_flag(room_key) not in flags:
        return None
    return TRAIL_HOME_HINTS.get(room_key)


async def _use_trail_marker(session, normalized: str) -> bool:
    commands = {
        "mark trail",
        "use trail marker",
        "use waxed trail marker",
        "place trail marker",
        "tie trail marker",
        "set trail marker",
    }
    if normalized not in commands:
        return False
    if session.character is None or session.character.race != "troll":
        return False

    quantity = session.database.item_quantity(session.character.id, TROLL_TRAIL_MARKER_KEY)
    if quantity <= 0:
        await session.send("\r\nYou do not have a Waxed Trail Marker to place.\r\n")
        return True

    room_key = session.character.current_room or ""
    if room_key == troll_start.TROLL_START_ROOM_KEY:
        await session.send("\r\nYou are already in Frostroot Camp. Harka would call using a return marker here a waste of good waxed hide.\r\n")
        return True
    hint = TRAIL_HOME_HINTS.get(room_key)
    if hint is None:
        await session.send(
            "\r\nHarka made this marker for Frostroot's nearby trails. You cannot identify a reliable authored return line from here, so you keep it rather than pretending.\r\n"
        )
        return True

    if not session.database.consume_item(session.character.id, TROLL_TRAIL_MARKER_KEY, 1):
        await session.send("\r\nYou reach for the marker and find it is no longer in your pack.\r\n")
        return True

    direction, destination = hint
    session.database.grant_flag(session.character.id, TROLL_TRAIL_MARKER_USED_FLAG)
    session.database.grant_flag(session.character.id, _marker_room_flag(room_key))
    await session.send(
        "\r\nYou score the nearby bark, tie Harka's waxed strip beneath the mark, and turn its notched point along the return side of the trail. Snow can cover prints; the dark wax and cut point should remain readable.\r\n"
        f"Your marker records the first safe leg home from here: {direction}, toward {destination}.\r\n"
        "The Waxed Trail Marker is consumed, but this character can CHECK MARKER here later to read the direction again.\r\n"
    )
    return True


async def _check_trail_marker(session, normalized: str) -> bool:
    if normalized not in {
        "check marker",
        "check trail marker",
        "look trail marker",
        "examine trail marker",
        "look marker",
        "examine marker",
    }:
        return False
    if session.character is None or session.character.race != "troll":
        return False
    hint = _current_marker_hint(session)
    if hint is None:
        return False
    direction, destination = hint
    await session.send(
        f"\r\nYour waxed trail marker is still tied here. Its notched point marks {direction} as the first safe leg back toward {destination}.\r\n"
    )
    return True


async def _eat_ration(session, normalized: str) -> bool:
    commands = {
        "eat smoked root ration",
        "eat root ration",
        "eat frostroot ration",
        "eat ration",
        "use smoked root ration",
        "use root ration",
    }
    if normalized not in commands:
        return False
    if session.character is None or session.character.race != "troll":
        return False
    if session.database.item_quantity(session.character.id, TROLL_RATION_KEY) <= 0:
        return False
    if session.combatant is None:
        await session.send("\r\nYour combat state is not available, so the ration cannot apply its recovery yet.\r\n")
        return True
    if session.combatant.current_hp >= session.combatant.max_hp:
        await session.send("\r\nYou are already at full HP. You keep Oda's ration for when eating it would actually help.\r\n")
        return True

    heal = SMOKED_ROOT_RATION.consumable.heal_hp if SMOKED_ROOT_RATION.consumable else 4
    before = session.combatant.current_hp
    restored = min(heal, session.combatant.max_hp - session.combatant.current_hp)
    if not session.database.consume_item(session.character.id, TROLL_RATION_KEY, 1):
        return True
    session.combatant.current_hp += restored
    session.database.grant_flag(session.character.id, TROLL_RATION_USED_FLAG)
    await session.send(
        f"\r\nYou eat the dense smoked root ration slowly enough to keep it down. It restores {restored} HP ({before} -> {session.combatant.current_hp}). The field ration is consumed.\r\n"
    )
    await session.send_client_state()
    return True


async def _brannik_choice_echo(session) -> bool:
    """Add one small callback before Brannik's normal first conversation."""
    if (
        session.character is None
        or session.character.race != "troll"
        or session.character.current_room != troll_start.TROLL_WINDSCAR_SHELF_KEY
    ):
        return False
    outsider = session.database.get_quest(session.character.id, troll_start.TROLL_OUTSIDER_QUEST.key)
    if (
        outsider is None
        or outsider.get("status") != "active"
        or outsider.get("current_step") != "meet_outsider"
        or TROLL_BRANNIK_CHOICE_ECHO_FLAG in _flags(session)
    ):
        return False

    flags = _flags(session)
    if survivor.TROLL_TRACK_ROUTE_COMPLETE_FLAG in flags:
        text = (
            "Before Brannik finishes looking you over, your attention goes past the heavy rear of the sledge to the runner grooves, drift edges, and the ground around the animal. The false retreat sign outside Frostroot taught you not to trust the most obvious line simply because it is obvious."
        )
    elif survivor.TROLL_CAMP_ROUTE_COMPLETE_FLAG in flags:
        text = (
            "Before Brannik finishes looking you over, your attention goes to what is under strain rather than what looks heaviest. The shelter row taught you to ask which problem is getting worse first, not which one is making the most noise."
        )
    else:
        return False

    session.database.grant_flag(session.character.id, TROLL_BRANNIK_CHOICE_ECHO_FLAG)
    await session.send("\r\n" + text + "\r\n")
    return True


async def _delegate_prompt(self, previous_playing_prompt, command: str) -> None:
    had_instance_prompt = "prompt" in self.__dict__
    previous_instance_prompt = self.__dict__.get("prompt")

    async def replay_prompt(_text: str) -> str:
        return command

    self.prompt = replay_prompt
    try:
        await previous_playing_prompt(self)
    finally:
        if had_instance_prompt:
            self.prompt = previous_instance_prompt
        else:
            self.__dict__.pop("prompt", None)


def install_troll_choice_echo_runtime(player_session_class, world_service) -> None:
    """Layer light later consequences on top of the two-route first-duty branch."""
    install_troll_choice_echo_content(world_service)
    if getattr(player_session_class, "_troll_choice_echo_runtime_installed", False):
        return

    previous_playing_prompt = player_session_class.playing_prompt

    async def playing_prompt(self) -> None:
        if self.character is None or self.character.race != "troll":
            await previous_playing_prompt(self)
            return

        await self.send_client_state()
        command = await self.prompt("\r\n> ")
        if command is None:
            self.state = type(self.state).DISCONNECTED
            return
        normalized = command.strip().lower()
        room = self.character.current_room or ""

        if normalized == "talk" or normalized.startswith("talk "):
            target = troll_start._talk_target(command)
            if room == troll_start.TROLL_TRACKLINE_VERGE_KEY and troll_start._matches(
                target,
                "harka",
                "scout",
                "scout harka",
                "harka pine-eye",
                "pine-eye",
            ):
                if await _talk_harka(self):
                    return
            if room == troll_start.TROLL_EMBER_HOLLOW_KEY and troll_start._matches(
                target,
                "oda",
                "hearthkeeper",
                "hearth keeper",
                "oda warmstone",
                "warmstone",
            ):
                if await _talk_oda(self):
                    return
            if room == troll_start.TROLL_WINDSCAR_SHELF_KEY and troll_start._matches(
                target,
                "brannik",
                "courier",
                "dwarf",
                "dwarven courier",
                "brannik slateboot",
                "slateboot",
            ):
                await _brannik_choice_echo(self)
                await _delegate_prompt(self, previous_playing_prompt, command)
                return

        if await _use_trail_marker(self, normalized):
            return
        if await _check_trail_marker(self, normalized):
            return
        if await _eat_ration(self, normalized):
            return

        await _delegate_prompt(self, previous_playing_prompt, command)

        if normalized in {"look", "l"}:
            hint = _current_marker_hint(self)
            if hint is not None:
                direction, destination = hint
                await self.send(
                    f"Your waxed trail marker is still tied here, its notched point indicating {direction} toward {destination}.\r\n"
                )
        if normalized in {"help", "?"} and survivor.TROLL_FIRST_DUTY_COMPLETE_FLAG in _flags(self):
            await self.send(
                "First-duty echoes: Scout Harka Pine-Eye is at Trackline Verge and Hearthkeeper Oda Warmstone is at Ember Hollow. Route-specific keepsakes use MARK TRAIL or EAT SMOKED ROOT RATION when applicable.\r\n"
            )

    player_session_class.playing_prompt = playing_prompt
    player_session_class._troll_choice_echo_runtime_installed = True
