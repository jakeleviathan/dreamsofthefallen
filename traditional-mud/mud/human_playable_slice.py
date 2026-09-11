from __future__ import annotations

from dataclasses import dataclass, replace

import mud.crafting as crafting
import mud.world as legacy_world
from mud.crafting import ItemDefinition
from mud.human_blackwall_opening import (
    HUMAN_BEYOND_WALL_QUEST_KEY,
    HUMAN_BURROWER_DEFEATED_FLAG,
    HUMAN_BURROWER_KEY,
    HUMAN_CARAVAN_QUEST_KEY,
    HUMAN_CINDER_WARD_KEY,
    HUMAN_EARTH_CACHE_QUEST_KEY,
    HUMAN_OPENING_GRANDFATHERED_FLAG,
    HUMAN_OUTER_CARAVAN_ROAD_KEY,
    HUMAN_READINESS_QUEST_KEY,
    HUMAN_SOOTSTEP_TUNNEL_KEY,
)
from mud.mechanics import PROGRESSION_RULES
from mud.room_engine import DescriptionLayer, ExitDefinition, FeatureDefinition, RoomAugmentation
from mud.stats import CharacterStats, EquipmentItem
from mud.world import RoomDefinition


HUMAN_FIRST_MILE_OVERLOOK_KEY = "human_first_mile_overlook"
HUMAN_SOOTSTEP_BRACERS_KEY = "human_sootstep_hide_bracers"

HUMAN_SLICE_FIRST_FIGHT_HELP_FLAG = "human_slice_first_fight_help_seen"
HUMAN_SLICE_FIRST_RESCUE_FLAG = "human_slice_first_burrower_rescue_used"
HUMAN_SLICE_BURROWER_LOOT_FLAG = "human_slice_burrower_loot_claimed"
HUMAN_SLICE_OVERLOOK_FLAG = "human_slice_first_mile_overlook_seen"


SOOTSTEP_HIDE_BRACERS = ItemDefinition(
    key=HUMAN_SOOTSTEP_BRACERS_KEY,
    name="Sootstep Hide Bracers",
    description=(
        "A pair of compact wrist guards cut from the Sootstep Burrower's slate-thick shoulder hide and laced with a clean length of recovered wagon leather. "
        "They are ugly, practical, and unmistakably tied to the first real danger you handled beneath Blackwall."
    ),
    category="equipment",
    equipment=EquipmentItem(
        name="Sootstep Hide Bracers",
        slot="hands",
        armor_class=1,
        stat_bonuses=CharacterStats(hp=1),
    ),
    tier=0,
)


HUMAN_FIRST_MILE_OVERLOOK = RoomDefinition(
    key=HUMAN_FIRST_MILE_OVERLOOK_KEY,
    name="First-Mile Overlook",
    region_key="human_kingdom",
    description=(
        "A short set of roadside steps climbs to a basalt shoulder above the caravan road. Blackwall fills the western view, huge and horned against the sky, while the land beyond it opens instead of closing: farm lanes, smoke from distant kiln towns, a pale northern road toward Dwarven country, and blue ridges stacked along the horizon. "
        "The overlook is not a monument. Teamsters stop here to tighten straps, travelers check weather, and somebody has wedged a chipped cup behind the milepost for whoever forgot one."
    ),
    exits={"west": HUMAN_OUTER_CARAVAN_ROAD_KEY},
    tags=("outside_city", "safe", "world_handoff", "vista", "human_start"),
)


def human_playable_slice_augmentations() -> dict[str, RoomAugmentation]:
    return {
        HUMAN_FIRST_MILE_OVERLOOK_KEY: RoomAugmentation(
            exit_overrides=(
                ExitDefinition(
                    "west",
                    HUMAN_OUTER_CARAVAN_ROAD_KEY,
                    "Outer Caravan Road",
                    travel_text="You descend the short roadside steps and return to the road beneath Blackwall.",
                ),
            ),
            features=(
                FeatureDefinition(
                    key="first_mile_post",
                    name="First-Mile Post",
                    aliases=("milepost", "post", "road post", "first mile post"),
                    summary="a weather-dark post crowded with practical route marks and scratched distances",
                    examine_text=(
                        "The nearest marks point back to Blackwall and toward local farms. Farther names include Stonewake Pass, the Copper Mile, Three Orchard, and roads whose distances are measured in days rather than streets. None of the marks promise destiny. They simply prove there is a great deal of Astralis beyond this district."
                    ),
                ),
                FeatureDefinition(
                    key="first_mile_view",
                    name="Open Horizon",
                    aliases=("horizon", "view", "roads", "distant roads", "mountains"),
                    summary="the first broad view of Astralis outside the shelter of the Human capital",
                    examine_text=(
                        "Blackwall is only one shape in the landscape from here. Wagons move like dark stitches along the northern road, field walls divide the low country, and the distant mountains are too far away to feel like scenery placed for your benefit. People already live there. Roads already matter there."
                    ),
                ),
            ),
            description_layers=(
                DescriptionLayer(
                    "first_mile_ordinary_pause",
                    "Wind moves over the rise carrying cut grass, road dust, and woodsmoke. A driver below argues cheerfully with a mule. Nothing is asking to be saved.",
                    priority=45,
                ),
            ),
        )
    }


def _replace_room(room: RoomDefinition) -> None:
    if room.key in legacy_world.ROOMS_BY_KEY:
        legacy_world.ROOMS = tuple(room if old.key == room.key else old for old in legacy_world.ROOMS)
    else:
        legacy_world.ROOMS = legacy_world.ROOMS + (room,)
    legacy_world.ROOMS_BY_KEY[room.key] = room


def _patch_outer_road() -> RoomDefinition:
    original = legacy_world.ROOMS_BY_KEY[HUMAN_OUTER_CARAVAN_ROAD_KEY]
    exits = dict(original.exits)
    exits["east"] = HUMAN_FIRST_MILE_OVERLOOK_KEY
    description = original.description
    if "roadside overlook" not in description.lower():
        description += (
            " A short flight of basalt steps climbs east to a roadside overlook used by teamsters checking the weather before longer journeys."
        )
    return replace(original, exits=exits, description=description)


def _register_item() -> None:
    if HUMAN_SOOTSTEP_BRACERS_KEY not in crafting.ITEMS_BY_KEY:
        crafting.ITEMS = crafting.ITEMS + (SOOTSTEP_HIDE_BRACERS,)
    crafting.ITEMS_BY_KEY[HUMAN_SOOTSTEP_BRACERS_KEY] = next(
        (item for item in crafting.ITEMS if item.key == HUMAN_SOOTSTEP_BRACERS_KEY),
        SOOTSTEP_HIDE_BRACERS,
    )


def install_human_playable_slice_content(world_service=None) -> None:
    """Register the first polished Human vertical slice additions idempotently."""
    _register_item()
    _replace_room(HUMAN_FIRST_MILE_OVERLOOK)
    outer = _patch_outer_road()
    _replace_room(outer)

    if world_service is None:
        return

    world_service.legacy_rooms[HUMAN_FIRST_MILE_OVERLOOK_KEY] = HUMAN_FIRST_MILE_OVERLOOK
    world_service.legacy_rooms[HUMAN_OUTER_CARAVAN_ROAD_KEY] = outer
    world_service.augmentations.update(human_playable_slice_augmentations())

    base = world_service.augmentations.get(HUMAN_OUTER_CARAVAN_ROAD_KEY, RoomAugmentation())
    exits = [item for item in base.exit_overrides if item.direction != "east"]
    exits.append(
        ExitDefinition(
            "east",
            HUMAN_FIRST_MILE_OVERLOOK_KEY,
            "First-Mile Overlook",
            travel_text="You leave the wagon ruts for a few steps and climb the basalt shoulder above the road.",
        )
    )
    world_service.augmentations[HUMAN_OUTER_CARAVAN_ROAD_KEY] = replace(base, exit_overrides=tuple(exits))

    cache = getattr(world_service, "_scene_cache", None)
    if cache is not None:
        cache.pop(HUMAN_FIRST_MILE_OVERLOOK_KEY, None)
        cache.pop(HUMAN_OUTER_CARAVAN_ROAD_KEY, None)


@dataclass(frozen=True, slots=True)
class SliceMilestone:
    quest_key: str
    label: str
    xp: int
    flag: str


@dataclass(frozen=True, slots=True)
class SliceAward:
    label: str
    xp: int
    old_level: int
    new_level: int
    total_experience: int


SLICE_MILESTONES: tuple[SliceMilestone, ...] = (
    SliceMilestone(HUMAN_READINESS_QUEST_KEY, "When the Wall Calls", 20, "human_slice_xp_readiness"),
    SliceMilestone(HUMAN_CARAVAN_QUEST_KEY, "A Wheel Does Not Lie", 25, "human_slice_xp_caravan"),
    SliceMilestone(HUMAN_EARTH_CACHE_QUEST_KEY, "The Wrong Kind of Old", 15, "human_slice_xp_earth_cache"),
    SliceMilestone(HUMAN_BEYOND_WALL_QUEST_KEY, "Beyond the Blackwall", 10, "human_slice_xp_beyond_wall"),
)


def _flags(session) -> set[str]:
    character = getattr(session, "character", None)
    if character is None:
        return set()
    return set(session.database.list_flags(character.id))


def _human(session) -> bool:
    character = getattr(session, "character", None)
    return bool(character and character.race == "human")


def reconcile_human_slice_progression(session) -> tuple[SliceAward, ...]:
    """Award the authored first-slice quest XP exactly once per milestone.

    The four quest rewards total 70 XP. The Sootstep Burrower already awards 30 XP,
    so a fresh Human who completes the intended Blackwall route lands exactly at
    the 100-XP level-two threshold without artificial grinding.
    """
    if not _human(session):
        return ()
    flags = _flags(session)
    if HUMAN_OPENING_GRANDFATHERED_FLAG in flags:
        return ()

    awards: list[SliceAward] = []
    for milestone in SLICE_MILESTONES:
        flags = _flags(session)
        if milestone.flag in flags:
            continue
        quest = session.database.get_quest(session.character.id, milestone.quest_key)
        if not quest or quest.get("status") != "completed":
            continue

        before = session.database.get_character_by_name(session.character.name) or session.character
        old_level = int(before.level)
        session.database.add_experience(session.character.id, milestone.xp)
        session.database.grant_flag(session.character.id, milestone.flag)
        refreshed = session.database.get_character_by_name(session.character.name)
        if refreshed is not None:
            session.character = refreshed
        awards.append(
            SliceAward(
                label=milestone.label,
                xp=milestone.xp,
                old_level=old_level,
                new_level=int(session.character.level),
                total_experience=int(session.character.experience),
            )
        )
    return tuple(awards)


async def announce_slice_awards(session, awards: tuple[SliceAward, ...]) -> None:
    for award in awards:
        await session.send(f"\r\nExperience: +{award.xp} XP - {award.label}.\r\n")
        if award.new_level > award.old_level:
            await session.send(
                f"*** LEVEL {award.new_level} ***\r\n"
                "Your character has grown beyond the opening rank. Type ABILITIES to see what your class can now do.\r\n"
            )
        else:
            next_total = PROGRESSION_RULES.cumulative_xp_for_level(award.new_level + 1)
            await session.send(
                f"Progress: {award.total_experience}/{next_total} total XP toward level {award.new_level + 1}.\r\n"
            )


def burrower_loot_available(session) -> bool:
    if not _human(session) or session.character.current_room != HUMAN_SOOTSTEP_TUNNEL_KEY:
        return False
    flags = _flags(session)
    return HUMAN_BURROWER_DEFEATED_FLAG in flags and HUMAN_SLICE_BURROWER_LOOT_FLAG not in flags


async def claim_burrower_loot(session) -> bool:
    if not burrower_loot_available(session):
        return False
    if session.database.item_quantity(session.character.id, HUMAN_SOOTSTEP_BRACERS_KEY) <= 0:
        session.database.add_item(session.character.id, HUMAN_SOOTSTEP_BRACERS_KEY, 1)
    session.database.grant_flag(session.character.id, HUMAN_SLICE_BURROWER_LOOT_FLAG)
    await session.send(
        "\r\nYou salvage two intact plates of slate-thick hide from the burrower's forelimbs and lace them with a clean length of the torn wagon leather. The result is crude, but solid enough to wear.\r\n"
        "\r\nLoot: Sootstep Hide Bracers [Hands | AC +1 | HP +1]\r\n"
        "Type COMPARE SOOTSTEP HIDE BRACERS to see how they fit your current gear, or EQUIP SOOTSTEP HIDE BRACERS to wear them.\r\n"
    )
    return True


def _first_rescue_eligible(session, enemy_name: str) -> bool:
    if not _human(session) or enemy_name.lower() != "sootstep burrower":
        return False
    if session.character.current_room != HUMAN_SOOTSTEP_TUNNEL_KEY:
        return False
    flags = _flags(session)
    if HUMAN_SLICE_FIRST_RESCUE_FLAG in flags:
        return False
    quest = session.database.get_quest(session.character.id, HUMAN_CARAVAN_QUEST_KEY)
    return bool(quest and quest.get("status") == "active" and quest.get("current_step") == "fight_burrower")


async def recover_first_burrower_defeat(session, enemy_name: str) -> bool:
    """Give the polished first dangerous fight one forgiving, explicit recovery."""
    if not _first_rescue_eligible(session, enemy_name):
        return False

    session.database.grant_flag(session.character.id, HUMAN_SLICE_FIRST_RESCUE_FLAG)
    session.database.set_character_room(session.character.id, HUMAN_CINDER_WARD_KEY)
    if session.combatant is not None:
        session.combatant.current_hp = session.combatant.max_hp
        session.combatant.current_mana = session.combatant.max_mana
    await session._stop_combat()
    refreshed = session.database.get_character_by_name(session.character.name)
    if refreshed is not None:
        session.character = refreshed

    await session.send(
        "\r\nThe burrower gets underneath your guard and the tunnel goes black.\r\n"
        "\r\nYou wake on a Cinder Ward watch bench with a bandage around your ribs and a cup of bitter tea going cold beside you. A maintenance runner found you near the Sootstep stair and hauled you back inside.\r\n"
        "This first Blackwall recovery costs no experience. Outside protected opening incidents, death returns you to your bind point and can cost XP earned within your current level.\r\n"
        "Your investigation is still active. Recover your bearings, then return east when you are ready to try the tunnel again.\r\n\r\n"
    )
    await session.show_current_room()
    await session.send_client_state()
    return True


async def _delegate_prompt(self, previous_playing_prompt, command: str) -> None:
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


def install_human_playable_slice_runtime(player_session_class, world_service=None) -> None:
    """Polish the Human opening into one complete first-session gameplay loop."""
    if getattr(player_session_class, "_human_playable_slice_runtime_installed", False):
        return

    install_human_playable_slice_content(world_service)
    previous_enter_character = player_session_class.enter_character
    previous_playing_prompt = player_session_class.playing_prompt
    previous_move_character = player_session_class.move_character
    previous_start_combat = player_session_class.start_combat
    previous_finish_enemy = player_session_class._finish_enemy_defeat
    previous_character_death = player_session_class._handle_character_death

    async def enter_character(self) -> None:
        await previous_enter_character(self)
        if not _human(self):
            return
        awards = reconcile_human_slice_progression(self)
        if awards:
            await announce_slice_awards(self, awards)
        if burrower_loot_available(self):
            await self.send(
                "\r\nThe defeated Sootstep Burrower is still here. Type LOOT BURROWER before you leave if you want to salvage something useful from the fight.\r\n"
            )

    async def move_character(self, direction: str) -> None:
        origin = self.character.current_room if self.character is not None else None
        await previous_move_character(self, direction)
        if not _human(self) or self.character.current_room != HUMAN_FIRST_MILE_OVERLOOK_KEY:
            return
        if origin == HUMAN_FIRST_MILE_OVERLOOK_KEY:
            return
        flags = _flags(self)
        if HUMAN_SLICE_OVERLOOK_FLAG in flags:
            return
        self.database.grant_flag(self.character.id, HUMAN_SLICE_OVERLOOK_FLAG)
        await self.send(
            "\r\nNo bell sounds. No quest appears. For a moment Astralis is simply a place around you: wagons on a distant road, somebody's cooking smoke, mountains that will still be there tomorrow.\r\n"
            "The structured Blackwall opening has done its job. When you want another direction, WEST returns to the city and the sealed cathedral note waiting there. For now, you are allowed to just look.\r\n"
        )

    async def start_combat(self, target_text: str) -> None:
        had_enemy = self.active_enemy is not None
        await previous_start_combat(self, target_text)
        if had_enemy or not _human(self) or self.active_enemy is None:
            return
        if self.active_enemy.definition.key != HUMAN_BURROWER_KEY:
            return
        flags = _flags(self)
        if HUMAN_SLICE_FIRST_FIGHT_HELP_FLAG in flags:
            return
        self.database.grant_flag(self.character.id, HUMAN_SLICE_FIRST_FIGHT_HELP_FLAG)
        await self.send(
            "\r\nCombat is live now: your normal weapon attacks repeat automatically. You can still type commands while they do.\r\n"
            "Type ABILITIES if you need to check your class tools, USE <ability> to act, HEALTH to check the fight, or FLEE to try to break away.\r\n"
        )

    async def _finish_enemy_defeat(self, enemy) -> None:
        is_burrower = bool(
            _human(self)
            and enemy.definition.key == HUMAN_BURROWER_KEY
        )
        await previous_finish_enemy(self, enemy)
        if not is_burrower or self.character is None:
            return
        if self.combatant is not None:
            await self.send(
                f"Combat ends. You steady yourself at {self.combatant.current_hp}/{self.combatant.max_hp} HP and {self.combatant.current_mana}/{self.combatant.max_mana} mana.\r\n"
            )
        if burrower_loot_available(self):
            await self.send(
                "The burrower's slate hide is thick enough to be useful. Type LOOT BURROWER before you SEARCH NEST.\r\n"
            )

    async def _handle_character_death(self, enemy_name: str) -> None:
        if await recover_first_burrower_defeat(self, enemy_name):
            return
        await previous_character_death(self, enemy_name)

    async def playing_prompt(self) -> None:
        if not _human(self):
            await previous_playing_prompt(self)
            return

        command = await self.prompt("\r\n> ")
        if command is None:
            state = getattr(self, "state", None)
            if state is not None and hasattr(type(state), "DISCONNECTED"):
                self.state = type(state).DISCONNECTED
            return
        normalized = " ".join(command.strip().lower().split())

        if normalized in {"loot", "loot burrower", "loot body", "loot corpse", "search body", "search burrower body"}:
            if await claim_burrower_loot(self):
                return
            if self.character.current_room == HUMAN_SOOTSTEP_TUNNEL_KEY:
                if HUMAN_BURROWER_DEFEATED_FLAG not in _flags(self):
                    await self.send("There is nothing safe to loot while the burrower is still alive.\r\n")
                else:
                    await self.send("You already took the useful hide from the burrower. The nest itself is separate evidence.\r\n")
                return

        await _delegate_prompt(self, previous_playing_prompt, command)
        if self.character is None:
            return

        awards = reconcile_human_slice_progression(self)
        if awards:
            await announce_slice_awards(self, awards)

        if normalized in {"look", "l"} and burrower_loot_available(self):
            await self.send("The defeated Sootstep Burrower lies beside the nest. You can LOOT BURROWER before continuing.\r\n")

    player_session_class.enter_character = enter_character
    player_session_class.move_character = move_character
    player_session_class.start_combat = start_combat
    player_session_class._finish_enemy_defeat = _finish_enemy_defeat
    player_session_class._handle_character_death = _handle_character_death
    player_session_class.playing_prompt = playing_prompt
    player_session_class._human_playable_slice_runtime_installed = True
