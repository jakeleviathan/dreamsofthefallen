from __future__ import annotations

import re
import zlib
from time import monotonic

import mud.combat as combat
import mud.crafting as crafting
import mud.economy_loop as economy
import mud.mechanics as mechanics
import mud.party_quality as party_quality
import mud.party_system as party_system
import mud.quests as quests
from mud.racial_abilities import (
    RACIAL_ACTIVE_ALIASES,
    RACIAL_ACTIVE_COOLDOWNS,
    RACIAL_ACTIVE_KEYS,
    RACIAL_TEXT,
)
from mud.equipment_system import equipped_definitions, equipped_item_keys
from mud.reflection_opportunities import reflection_opportunities
from mud.room_engine import PlayerRoomContext
from mud.room_player_presence import room_player_entries
from mud.style_collectibles import style_atelier_available
from mud.weather_gameplay import effects_for_weather, room_is_weather_exposed, surface_condition
from mud.world import NPCS_BY_KEY


MODERN_CLIENT_VERSION = "2.0.0"

# This layer deliberately keeps the ordinary Telnet text game authoritative.
# GMCP-capable clients get a second, structured view of the same state instead of
# replacing commands with a proprietary protocol. A plain terminal can still do
# everything a polished Mudlet package can do.


def stable_room_number(room_key: str) -> int:
    """Return a stable positive mapper id for a room key.

    Python's built-in hash is intentionally process-randomized, so use CRC32 for
    the client mapper. The +1 avoids Mudlet's special zero/false-ish cases.
    """
    return (zlib.crc32(room_key.encode("utf-8")) & 0x7FFFFFFF) + 1


def _room_context(session, world) -> PlayerRoomContext | None:
    character = getattr(session, "character", None)
    if character is None:
        return None
    return PlayerRoomContext(
        character_id=int(character.id),
        race_key=character.race or "",
        class_key=character.character_class or "",
        level=int(character.level),
        character_flags=session.database.list_flags(character.id),
        hour=int(getattr(session, "astralis_hour", 12)),
        weather=world.state.weather_for(
            world.scene(character.current_room or "").region_key
            if world.scene(character.current_room or "") is not None
            else ""
        ),
    )


def _room_snapshot(session, world) -> dict | None:
    character = getattr(session, "character", None)
    if character is None or not character.current_room:
        return None
    context = _room_context(session, world)
    if context is None:
        return None
    view = world.build_view(character.current_room, context)
    scene = world.scene(character.current_room)
    if view is None or scene is None:
        return None

    exits = {
        visible.direction: stable_room_number(visible.destination_key)
        for visible in view.exits
    }
    exit_keys = {
        visible.direction: visible.destination_key
        for visible in view.exits
    }
    features = [
        {
            "key": feature.key,
            "name": feature.name,
            "summary": feature.summary,
            "can_examine": bool(feature.examine_text or feature.summary),
            "can_search": bool(feature.search_text),
            "can_touch": bool(feature.touch_text),
            "can_listen": bool(feature.listen_text),
            "can_use": False,
        }
        for feature in view.features
    ]
    weather = world.state.weather_for(scene.region_key)
    exposed = room_is_weather_exposed(scene.tags, scene.key)
    for source in reflection_opportunities(scene, weather, exposed=exposed):
        if any(feature["name"] == source.name for feature in features):
            continue
        features.append(
            {
                "key": f"reflection:{source.key}",
                "name": source.name,
                "summary": source.room_text,
                "can_examine": True,
                "can_search": False,
                "can_touch": False,
                "can_listen": False,
                "can_use": True,
            }
        )

    return {
        "key": view.key,
        "num": stable_room_number(view.key),
        "name": view.name,
        "zone": scene.region_key,
        "description": view.description,
        "tags": list(view.tags),
        "exits": exits,
        "exit_keys": exit_keys,
        "features": features,
        "players": [
            {"name": name, "description": description, "is_self": name.endswith(" (you)")}
            for name, description in room_player_entries(session)
        ],
    }


def _inventory_snapshot(session) -> dict:
    from mud.item_heritage import heritage_inventory_summaries

    character = session.character
    equipment = equipped_item_keys(session.database, character.id)
    heritage_by_item = heritage_inventory_summaries(session.database, character.id)
    equipped_by_item = {item_key: slot for slot, item_key in equipment.items()}
    items = []
    for row in session.database.list_items(character.id):
        item_key = str(row["item_key"])
        definition = crafting.ITEMS_BY_KEY.get(item_key)
        heritage = heritage_by_item.get(item_key)
        items.append(
            {
                "key": item_key,
                "name": definition.name if definition is not None else item_key.replace("_", " ").title(),
                "quantity": int(row["quantity"]),
                "category": definition.category if definition is not None else "unknown",
                "tier": int(definition.tier) if definition is not None else 0,
                "equipped": item_key in equipped_by_item,
                "slot": equipped_by_item.get(item_key, ""),
                "description": definition.description if definition is not None else "",
                "heritage": heritage,
            }
        )
    items.sort(key=lambda value: (not value["equipped"], value["category"], value["name"].lower()))
    from mud.inventory_capacity import inventory_capacity_status
    slots_used, slots_capacity = inventory_capacity_status(session.database, character.id)
    return {
        "count": sum(int(item["quantity"]) for item in items),
        "unique": len(items),
        "slots_used": slots_used,
        "slots_capacity": slots_capacity,
        "over_capacity": slots_used > slots_capacity,
        "items": items,
        "equipment": equipment,
    }


def _quest_snapshot(session) -> dict:
    rows = session.database.list_quests(session.character.id)
    active = []
    completed = []
    for row in rows:
        definition = quests.QUESTS_BY_KEY.get(str(row["quest_key"]))
        entry = {
            "key": str(row["quest_key"]),
            "name": definition.name if definition is not None else str(row["quest_key"]).replace("_", " ").title(),
            "status": str(row["status"]),
            "step": str(row["current_step"] or ""),
            "objective": (
                definition.objective_for_step(str(row["current_step"]))
                if definition is not None and row["current_step"] is not None
                else None
            ) or "",
            "description": definition.description if definition is not None else "",
        }
        if entry["status"] == "active":
            active.append(entry)
        else:
            completed.append(entry)
    return {"active": active, "completed_count": len(completed)}


def _ability_target_mode(ability) -> str:
    if ability.key == "resurrection":
        return "dead_ally"
    if ability.category in {"healing", "ally_buff", "healing_over_time", "ally_protection", "protection"}:
        return "ally"
    if ability.category in {"group_healing", "group_protection"}:
        return "group"
    if ability.category in {"self_protection", "spell_setup", "class_passive_utility"}:
        return "self"
    return "enemy"


def _ability_command(ability) -> str:
    if ability.key == "resurrection":
        return "RESURRECT"
    if ability.key == "forage":
        return "FORAGE"
    if ability.key == "taunt":
        return "TAUNT"
    if ability.key == "raise_skeleton":
        return "RAISE SKELETON"
    return "CAST " + ability.name.upper()


def _racial_hotbar_entries(session, now: float) -> list[dict]:
    """Expose the character's active racial ability through Dreams.Abilities.

    The Mudlet hotbar intentionally consumes one unified action catalog. Racial
    actives therefore live beside learned class abilities instead of requiring
    a second race-only UI. Human Adapt is parameterized, so its four legal stat
    choices are exposed as four independently assignable hotbar actions while
    sharing the same underlying racial cooldown.
    """

    character = getattr(session, "character", None)
    if character is None:
        return []
    race_key = character.race or ""
    active_key = RACIAL_ACTIVE_KEYS.get(race_key)
    authored = RACIAL_TEXT.get(race_key)
    aliases = RACIAL_ACTIVE_ALIASES.get(race_key, ())
    cooldown = RACIAL_ACTIVE_COOLDOWNS.get(race_key)
    if active_key is None or authored is None or not aliases or cooldown is None:
        return []

    _passive_name, _passive_description, ability_name, description = authored
    combatant = getattr(session, "combatant", None)
    ready_at = (
        float(combatant.cooldowns.get(active_key, 0.0))
        if combatant is not None
        else 0.0
    )
    remaining = max(0.0, ready_at - now)
    ready = remaining <= 0.0
    target_mode = "enemy" if race_key == "troll" else "group" if race_key == "sporekin" else "self"

    def entry(*, key: str, name: str, command: str) -> dict:
        return {
            "key": key,
            "name": name,
            "category": "racial",
            "description": description,
            "mana": 0,
            "cooldown": float(cooldown),
            "cooldown_remaining": remaining,
            "ready": ready,
            "target_mode": target_mode,
            "command": command,
            "source": "racial",
            "race": race_key,
        }

    if race_key == "human":
        return [
            entry(
                key=f"{active_key}_{stat}",
                name=f"{ability_name}: {stat.title()}",
                command=f"RACIAL {aliases[0].upper()} {stat.upper()}",
            )
            for stat in ("might", "grace", "love", "mind")
        ]

    return [
        entry(
            key=active_key,
            name=ability_name,
            command=f"RACIAL {aliases[0].upper()}",
        )
    ]


def _ability_snapshot(session) -> dict:
    character = session.character
    combatant = getattr(session, "combatant", None)
    abilities = mechanics.class_abilities_for_level(
        character.character_class or "", character.level, character.deity_key
    )
    now = monotonic()
    result = []
    for ability in abilities:
        ready_at = 0.0
        if combatant is not None:
            ready_at = float(combatant.cooldowns.get(ability.key, 0.0))
        result.append(
            {
                "key": ability.key,
                "name": ability.name,
                "category": ability.category,
                "description": ability.description,
                "mana": int(ability.mana_cost or 0),
                "cooldown": float(ability.cooldown_seconds or 0.0),
                "cooldown_remaining": max(0.0, ready_at - now),
                "ready": combatant.ability_ready(ability.key, now) if combatant is not None else True,
                "target_mode": _ability_target_mode(ability),
                "command": _ability_command(ability),
                "source": "class",
            }
        )
    result.extend(_racial_hotbar_entries(session, now))
    return {
        "class": character.character_class or "",
        "level": int(character.level),
        "abilities": result,
    }


def _weather_effect_entries(session, world) -> list[dict]:
    """Return only weather mechanics that currently affect this character."""

    character = getattr(session, "character", None)
    if character is None or world is None or not character.current_room:
        return []

    scene = world.scene(character.current_room)
    if scene is None or not room_is_weather_exposed(scene.tags, scene.key):
        return []

    weather = world.state.weather_for(scene.region_key)
    weather_label = weather.replace("_", " ").title()
    mechanics_effects = effects_for_weather(weather, exposed=True)
    result: list[dict] = []

    def add(key: str, name: str, detail: str) -> None:
        result.append(
            {
                "key": key,
                "name": name,
                "kind": "weather",
                "detail": detail,
                "remaining": None,
            }
        )

    concealment = float(mechanics_effects.concealment_bonus)
    if concealment > 0:
        percent = int(round(concealment * 100))
        add(
            "weather_concealment",
            f"{weather_label}: Concealment",
            (
                f"+{percent} percentage points to flee chance; hostile roaming NPCs "
                f"have a {percent}% chance to fail to notice you."
            ),
        )

    footing = surface_condition(scene.tags, weather, exposed=True)
    if footing is not None:
        add(
            f"weather_footing_{footing.key}",
            f"{weather_label}: {footing.key.title()} Footing",
            (
                f"Outdoor movement is slowed by {footing.travel_delay_seconds:g} seconds here. "
                f"{footing.text}"
            ),
        )

    main_hand = equipped_definitions(session.database, character.id).get("main_hand")
    equipment = getattr(main_hand, "equipment", None)
    if (
        mechanics_effects.ranged_attack_penalty > 0
        and equipment is not None
        and bool(getattr(equipment, "is_ranged", False))
    ):
        add(
            "weather_ranged_interference",
            f"{weather_label}: Ranged Interference",
            f"-{mechanics_effects.ranged_attack_penalty} to outdoor ranged attack rolls.",
        )

    has_fire_magic = any(
        str(getattr(ability, "element", "") or "").lower() == "fire"
        for ability in mechanics.class_abilities_for_level(
            character.character_class or "",
            character.level,
            getattr(character, "deity_key", None),
        )
    )
    if mechanics_effects.fire_disruption_chance > 0 and has_fire_magic:
        percent = int(round(mechanics_effects.fire_disruption_chance * 100))
        add(
            "weather_fire_disruption",
            f"{weather_label}: Fire Disruption",
            f"{percent}% chance an outdoor fire spell is disrupted when cast.",
        )

    return result


def _effects_snapshot(session, world=None) -> dict:
    """Return active player effects for structured clients.

    Effects remain authoritative on the server. Timed class effects include
    approximate remaining durations, while weather entries remain active until
    the character reaches cover or the regional conditions change.
    """
    now = monotonic()
    result: list[dict] = []

    def add(key: str, name: str, kind: str, detail: str, until: float | None) -> None:
        remaining = None
        if until is not None and until > 0:
            remaining = max(0.0, float(until) - now)
            if remaining <= 0:
                return
            remaining = round(remaining, 1)
        result.append(
            {
                "key": key,
                "name": name,
                "kind": kind,
                "detail": detail,
                "remaining": remaining,
            }
        )

    resolve_amount = int(getattr(session, "_priest_resolve_blessing", 0) or 0)
    if resolve_amount:
        add(
            "blessing_of_resolve",
            "Blessing of Resolve",
            "buff",
            f"+{resolve_amount} maximum Health",
            float(getattr(session, "_priest_resolve_blessing_until", 0.0) or 0.0),
        )

    if bool(getattr(session, "_oakheart_active", False)):
        oakheart_amount = int(getattr(session, "_oakheart_amount", 0) or 0)
        add(
            "oakheart",
            "Oakheart",
            "buff",
            f"+{oakheart_amount} maximum Health" if oakheart_amount else "Maximum Health increased",
            float(getattr(session, "_oakheart_until", 0.0) or 0.0),
        )

    ward_until = float(getattr(session, "ward_until", 0.0) or 0.0)
    if ward_until > now:
        add(
            "protective_ward",
            str(getattr(session, "_ward_effect_name", "") or "Protective Ward"),
            "ward",
            "Incoming damage is being softened",
            ward_until,
        )

    arcane_until = float(getattr(session, "_arcane_surge_until", 0.0) or 0.0)
    if arcane_until > now:
        add(
            "arcane_surge",
            "Arcane Surge",
            "buff",
            "Empowers your next damaging Wizard spell",
            arcane_until,
        )

    rejuvenation_until = float(getattr(session, "_rejuvenation_until", 0.0) or 0.0)
    if rejuvenation_until > now:
        add(
            "rejuvenation",
            "Rejuvenation",
            "healing",
            "Healing pulses are still active",
            rejuvenation_until,
        )

    result.extend(_weather_effect_entries(session, world))
    result.sort(key=lambda effect: (effect["kind"], effect["name"].lower()))
    return {"effects": result}


def _party_snapshot(session) -> dict:
    character = session.character
    party = party_system._party_for_session(session)
    if party is None:
        nearby = []
        try:
            for other in party_quality._nearby_open_sessions(session):
                other_character = getattr(other, "character", None)
                if other_character is not None:
                    nearby.append({"name": other_character.name, "level": other_character.level})
        except Exception:
            nearby = []
        return {"active": False, "members": [], "nearby": nearby}

    top_aggro = None
    enemy = getattr(session, "active_enemy", None)
    if enemy is not None:
        top_aggro = enemy.hate.top_target()
    ready_ids = party_quality._READY_BY_PARTY.get(id(party), set())
    ready_active = id(party) in party_quality._READY_BY_PARTY
    focus = party_quality._FOCUS_BY_PARTY.get(id(party), "")

    members = []
    for member_id in party.member_ids:
        other = party_system._session_for_character_id(member_id)
        other_character = getattr(other, "character", None) if other is not None else None
        other_combatant = getattr(other, "combatant", None) if other is not None else None
        if other_character is None:
            members.append(
                {
                    "id": int(member_id),
                    "name": f"Character #{member_id}",
                    "online": False,
                    "leader": member_id == party.leader_id,
                    "here": False,
                    "follow": member_id in party.follow_ids,
                    "ready": member_id in ready_ids if ready_active else None,
                    "dead": False,
                    "aggro": False,
                }
            )
            continue
        hp = int(other_combatant.current_hp) if other_combatant is not None else 0
        max_hp = int(other_combatant.max_hp) if other_combatant is not None else 1
        members.append(
            {
                "id": int(member_id),
                "name": other_character.name,
                "level": int(other_character.level),
                "online": True,
                "leader": member_id == party.leader_id,
                "here": other_character.current_room == character.current_room,
                "follow": member_id in party.follow_ids,
                "ready": member_id in ready_ids if ready_active else None,
                "dead": bool(getattr(other, "_death_pending", False)) or hp <= 0,
                "aggro": int(top_aggro) == int(member_id) if top_aggro is not None else False,
                "hp": hp,
                "max_hp": max_hp,
                "hp_percent": round(100 * hp / max(1, max_hp)),
            }
        )
    return {
        "active": True,
        "leader_id": int(party.leader_id),
        "loot_mode": party.loot_mode,
        "focus": focus,
        "ready_check": ready_active,
        "members": members,
        "nearby": [],
    }


def _feature_action(feature: dict) -> dict | None:
    target = feature["name"]
    if feature.get("can_use"):
        return {"label": f"Use {target}", "command": f"USE {target}", "kind": "inspect"}
    if feature.get("can_examine"):
        return {"label": f"Examine {target}", "command": f"EXAMINE {target}", "kind": "inspect"}
    if feature.get("can_listen"):
        return {"label": f"Listen: {target}", "command": f"LISTEN {target}", "kind": "inspect"}
    if feature.get("can_search"):
        return {"label": f"Search {target}", "command": f"SEARCH {target}", "kind": "inspect"}
    return None


def _context_actions(session, world, room: dict | None) -> dict:
    if room is None:
        return {"actions": []}
    actions: list[dict] = []
    character = session.character
    scene = world.scene(character.current_room or "")

    if getattr(session, "active_enemy", None) is not None:
        actions.append({"label": "Flee", "command": "FLEE", "kind": "danger", "primary": True})
    else:
        for direction in room["exits"].keys():
            actions.append(
                {
                    "label": direction.upper(),
                    "command": direction.upper(),
                    "kind": "move",
                    "primary": len(actions) == 0,
                }
            )

    if scene is not None:
        for npc_key in scene.npc_keys[:2]:
            npc = NPCS_BY_KEY.get(npc_key)
            if npc is not None:
                actions.append({"label": f"Talk: {npc.name}", "command": f"TALK {npc.name}", "kind": "talk"})
        for enemy_key in scene.enemy_keys[:1]:
            enemy = combat.ENEMIES_BY_KEY.get(enemy_key)
            if enemy is not None and getattr(session, "active_enemy", None) is None:
                selected = getattr(session, "selected_enemy", None)
                if selected is not None and selected.definition.key == enemy.key:
                    actions.append({"label": f"Attack {enemy.name}", "command": "ATTACK", "kind": "combat"})
                else:
                    actions.append({"label": f"Target {enemy.name}", "command": f"TARGET {enemy.name}", "kind": "target"})

    for feature in room.get("features", [])[:2]:
        action = _feature_action(feature)
        if action is not None:
            actions.append(action)

    room_key = character.current_room or ""
    if style_atelier_available(world, room_key):
        actions.append({"label": "Atelier", "command": "ATELIER", "kind": "style"})
    if economy.ROOM_RESOURCE_NODE_KEYS.get(room_key):
        actions.append({"label": "Resources", "command": "RESOURCES", "kind": "craft"})
    if economy.ROOM_STATIONS.get(room_key):
        actions.append({"label": "Recipes", "command": "RECIPES", "kind": "craft"})

    actions.extend(
        [
            {"label": "Quests", "command": "QUESTS", "kind": "panel"},
            {"label": "Inventory", "command": "INVENTORY", "kind": "panel"},
            {"label": "Class", "command": "CLASS", "kind": "panel"},
            {"label": "Party", "command": "PARTY HUD", "kind": "panel"},
        ]
    )
    # The Mudlet package has space for ten high-value actions. Server ordering is
    # intentional: immediate room/combat verbs win over utility panels.
    return {"actions": actions[:10]}


_ONBOARDING_FLAGS = {
    "movement": "modern_onboarding_movement",
    "reference": "modern_onboarding_reference",
    "combat": "modern_onboarding_combat",
    "ability": "modern_onboarding_ability",
}


def _onboarding_snapshot(session, room: dict | None) -> dict:
    flags = session.database.list_flags(session.character.id)
    if all(flag in flags for flag in _ONBOARDING_FLAGS.values()):
        return {"active": False, "stage": "complete", "title": "", "text": "", "command": ""}

    if _ONBOARDING_FLAGS["movement"] not in flags:
        first_exit = next(iter((room or {}).get("exits", {})), "LOOK")
        return {
            "active": True,
            "stage": "movement",
            "title": "Read the room, then move",
            "text": "Rooms are the world. Read what is here, then choose an exit; the map reveals itself as you travel.",
            "command": first_exit.upper(),
        }
    if _ONBOARDING_FLAGS["reference"] not in flags:
        return {
            "active": True,
            "stage": "reference",
            "title": "Keep your objective visible",
            "text": "QUESTS tells you what your current story expects without replacing exploration. INVENTORY shows what the world has put in your hands.",
            "command": "QUESTS",
        }
    if _ONBOARDING_FLAGS["combat"] not in flags:
        return {
            "active": True,
            "stage": "combat",
            "title": "Combat runs in real time",
            "text": "ATTACK starts automatic weapon swings. Your class abilities happen on top of those swings; FLEE is how you break away.",
            "command": "CLASS",
        }
    return {
        "active": True,
        "stage": "ability",
        "title": "Use the class, not just the weapon",
        "text": "Your hotbar is your class kit. Use an ability during a real fight; abilities improve through use and new tools unlock as you level.",
        "command": "CLASS",
    }


def _mark_onboarding_command(session, command: str) -> None:
    normalized = " ".join(command.strip().lower().split())
    if not normalized:
        return
    directions = {"north", "south", "east", "west", "up", "down", "n", "s", "e", "w", "u", "d"}
    if normalized in directions:
        session.database.grant_flag(session.character.id, _ONBOARDING_FLAGS["movement"])
    if normalized in {"quests", "quest", "inventory", "inv", "i", "help", "class", "role"}:
        session.database.grant_flag(session.character.id, _ONBOARDING_FLAGS["reference"])
    if normalized.startswith(("attack ", "kill ", "assist")):
        session.database.grant_flag(session.character.id, _ONBOARDING_FLAGS["combat"])
    if normalized.startswith(("cast ", "taunt", "forage", "raise skeleton", "resurrect ", "racial ")):
        session.database.grant_flag(session.character.id, _ONBOARDING_FLAGS["ability"])


def _event_snapshot(session) -> list[dict]:
    """Build significant state-transition events for subtle client cues."""
    events: list[dict] = []
    character = session.character
    combatant = getattr(session, "combatant", None)
    enemy = getattr(session, "active_enemy", None)

    room_key = character.current_room or ""
    previous_room = getattr(session, "_modern_last_room", None)
    if previous_room is not None and room_key != previous_room:
        events.append({"kind": "room", "intensity": "soft"})
    session._modern_last_room = room_key

    previous_level = getattr(session, "_modern_last_level", character.level)
    if character.level > previous_level:
        events.append({"kind": "level_up", "intensity": "strong", "level": character.level})
    session._modern_last_level = character.level

    target_key = enemy.definition.key if enemy is not None else ""
    previous_target = getattr(session, "_modern_last_target", "")
    if target_key and not previous_target:
        events.append({"kind": "combat_start", "intensity": "medium"})
    elif previous_target and not target_key:
        events.append({"kind": "combat_end", "intensity": "soft"})
    session._modern_last_target = target_key

    if combatant is not None:
        ratio = combatant.current_hp / max(1, combatant.max_hp)
        previous_ratio = getattr(session, "_modern_last_hp_ratio", 1.0)
        if ratio <= 0.25 < previous_ratio:
            events.append({"kind": "critical", "intensity": "strong"})
        elif ratio <= 0.50 < previous_ratio:
            events.append({"kind": "wounded", "intensity": "medium"})
        session._modern_last_hp_ratio = ratio

    aggro = enemy.hate.top_target() if enemy is not None else None
    previous_aggro = getattr(session, "_modern_last_aggro", None)
    if aggro is not None and aggro != previous_aggro and int(aggro) == int(character.id):
        events.append({"kind": "aggro", "intensity": "medium"})
    session._modern_last_aggro = aggro

    return events


async def _send_if_changed(session, package: str, payload) -> bool:
    cache = getattr(session, "_modern_gmcp_cache", None)
    if cache is None:
        cache = {}
        session._modern_gmcp_cache = cache
    if cache.get(package) == payload:
        return False
    cache[package] = payload
    return await session.telnet.send_gmcp(package, payload)


async def push_modern_state(session, world, *, full: bool = False) -> None:
    if (
        getattr(session, "character", None) is None
        or getattr(session, "combatant", None) is None
        or not session.telnet.gmcp_enabled
    ):
        return

    room = _room_snapshot(session, world)
    if room is not None:
        # Room.Info is a standard GMCP surface used by multiple MUD clients. The
        # Dreams.Room extension carries richer text, feature, and string-key data.
        await _send_if_changed(
            session,
            "Room.Info",
            {
                "num": room["num"],
                "name": room["name"],
                "zone": room["zone"],
                "details": room["tags"],
                "exits": room["exits"],
            },
        )
        await _send_if_changed(session, "Dreams.Room", room)

    await _send_if_changed(session, "Dreams.Party", _party_snapshot(session))
    await _send_if_changed(session, "Dreams.Abilities", _ability_snapshot(session))
    await _send_if_changed(session, "Dreams.Effects", _effects_snapshot(session, world))
    await _send_if_changed(session, "Dreams.Context", _context_actions(session, world, room))
    await _send_if_changed(session, "Dreams.Onboarding", _onboarding_snapshot(session, room))

    if full:
        await _send_if_changed(session, "Dreams.Inventory", _inventory_snapshot(session))
        await _send_if_changed(session, "Dreams.Quests", _quest_snapshot(session))

    for event in _event_snapshot(session):
        # Events are intentionally not de-duplicated: each transition is a cue.
        await session.telnet.send_gmcp("Dreams.Event", event)


async def _delegate_prompt(self, previous_prompt, command: str) -> None:
    had_prompt = "prompt" in self.__dict__
    old_prompt = self.__dict__.get("prompt")

    async def replay_prompt(_text: str):
        return command

    self.prompt = replay_prompt
    try:
        await previous_prompt(self)
    finally:
        if had_prompt:
            self.prompt = old_prompt
        else:
            self.__dict__.pop("prompt", None)


def install_modern_client_runtime(player_session_class, world) -> None:
    """Install the modern structured-client layer outside the complete game stack."""
    if getattr(player_session_class, "_modern_client_runtime_installed", False):
        return

    previous_enter = player_session_class.enter_character
    previous_playing_prompt = player_session_class.playing_prompt
    previous_send_client_state = player_session_class.send_client_state
    previous_show_room = player_session_class.show_current_room

    async def send_client_state(self) -> None:
        await previous_send_client_state(self)
        await push_modern_state(self, world, full=False)

    async def enter_character(self) -> None:
        await previous_enter(self)
        if self.character is not None and self.combatant is not None:
            # Seed transition state so merely logging in does not fire danger or
            # level-up cues. The first room still appears immediately in the map.
            self._modern_last_level = self.character.level
            self._modern_last_room = self.character.current_room or ""
            self._modern_last_hp_ratio = self.combatant.current_hp / max(1, self.combatant.max_hp)
            self._modern_last_target = ""
            self._modern_last_aggro = None
            await push_modern_state(self, world, full=True)

    async def show_current_room(self) -> None:
        await previous_show_room(self)
        if self.character is not None and self.combatant is not None:
            await push_modern_state(self, world, full=True)

    async def playing_prompt(self) -> None:
        if self.character is None:
            await previous_playing_prompt(self)
            return
        command = await self.prompt("\r\n> ")
        if command is None:
            self.state = type(self.state).DISCONNECTED
            return
        normalized = " ".join(command.strip().lower().split())

        if normalized in {"client", "ui", "hud", "modern ui", "client status"}:
            await self.send(
                "\r\nDreams of the Fallen remains fully playable through plain Telnet.\r\n"
                "GMCP clients receive structured room, mapper, quest, inventory, party, ability, and context data.\r\n"
                "Mudlet can install the official DreamsOfTheFallenHUD package through Client.GUI when server packages are allowed.\r\n"
                f"Structured client protocol: {MODERN_CLIENT_VERSION}.\r\n"
            )
            await push_modern_state(self, world, full=True)
            return

        await _delegate_prompt(self, previous_playing_prompt, command)
        if self.character is not None and self.combatant is not None:
            _mark_onboarding_command(self, command)
            await push_modern_state(self, world, full=True)

    player_session_class.send_client_state = send_client_state
    player_session_class.enter_character = enter_character
    player_session_class.show_current_room = show_current_room
    player_session_class.playing_prompt = playing_prompt
    player_session_class._modern_client_runtime_installed = True
