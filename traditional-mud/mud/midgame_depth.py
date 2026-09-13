from __future__ import annotations

from dataclasses import replace

import mud.crafting as crafting
import mud.quests as quests
import mud.world as legacy_world
from mud.broken_reach_midgame import (
    HILL_WARDEN_KEY,
    HOUSE_KEEPER_LOCK_KEY,
    HOUSE_THRESHOLD_KEY,
    ROOK_KEY,
)
from mud.crafting import ItemDefinition
from mud.quests import QuestDefinition
from mud.room_engine import ExitDefinition, RoomAugmentation, ViewCondition
from mud.salt_kingdoms_midgame import (
    BALLAST_MATRIARCH_KEY,
    GLASS_KEEL_BALLAST_KEY,
    GLASS_KEEL_CAPTAIN_KEY,
    GLASS_KEEL_COMPLETE_FLAG,
    KEELSPIRE_HARBOR_VAULT_KEY,
    KEELSPIRE_QUAYS_KEY,
    ODDITY_CUP_FLAG,
    ORRO_KEY,
    SLUICE_REGENT_KEY,
    TAVIK_KEY,
    UNDERTIDE_PRESSURE_WALK_KEY,
    UNDERTIDE_REGENT_KEY,
    UNDERTIDE_RELEASE_KEY,
)
from mud.stats import CharacterStats, EquipmentItem
from mud.world import RoomDefinition


# ---------------------------------------------------------------------------
# Named objects: memorable, restrained, and tied to actual places or bosses.
# ---------------------------------------------------------------------------
WARDENS_IRON_KEY = "depth_wardens_iron"
BRINEGLASS_KNIFE_KEY = "depth_brineglass_knife"
CAPTAINS_TIDEGLASS_KEY = "depth_captains_tideglass"
REGENT_VALVE_CROWN_KEY = "depth_regent_valve_crown"
ONE_THIRD_CUP_KEY = "depth_one_third_cup"
LOCKMAKERS_MARGIN_KEY = "depth_lockmakers_margin"
LAST_CARGO_MANIFEST_KEY = "depth_last_cargo_manifest"
QUIET_GAUGE_KEY = "depth_quiet_gauge"

NAMED_DEPTH_ITEMS = (
    ItemDefinition(
        WARDENS_IRON_KEY,
        "Warden's Iron",
        "A palm-sized plate broken from the Hill Warden's lock-body. Three stress lines meet in the center, making it look less like armor than a diagram of responsibility.",
        "equipment",
        equipment=EquipmentItem(
            "Warden's Iron", "accessory", armor_class=1,
            stat_bonuses=CharacterStats(hp=4, might=1),
            scripted_effects=("A keepsake from the Hill Warden's first-clear mechanics; no hidden proc.",),
        ),
        tier=4,
    ),
    ItemDefinition(
        BRINEGLASS_KNIFE_KEY,
        "Brineglass Knife",
        "A short working knife ground from blue-white mineral glass found under the Ballast Matriarch's nest. It is beautiful only because somebody kept sharpening it.",
        "equipment",
        equipment=EquipmentItem(
            "Brineglass Knife", "main_hand",
            stat_bonuses=CharacterStats(might=2, grace=2),
            scripted_effects=("No scripted proc; its identity is its source and stat profile.",),
        ),
        tier=5,
    ),
    ItemDefinition(
        CAPTAINS_TIDEGLASS_KEY,
        "Captain's Tideglass",
        "A thumb-sized sealed tideglass from the Glass Keel's private locker. The liquid inside makes tiny corrections when carried near deep running water.",
        "equipment",
        equipment=EquipmentItem(
            "Captain's Tideglass", "accessory",
            stat_bonuses=CharacterStats(mind=2, grace=1, love=1),
            scripted_effects=("Flavor clue: the tideglass trembles near authored water secrets.",),
        ),
        tier=5,
    ),
    ItemDefinition(
        REGENT_VALVE_CROWN_KEY,
        "Sluice Regent's Valve-Crown",
        "The bronze vane-crown from the Sluice Regent, each fin stamped with a different pressure limit. Several are worn thin from centuries of emergency correction.",
        "equipment",
        equipment=EquipmentItem(
            "Sluice Regent's Valve-Crown", "head", armor_class=2,
            stat_bonuses=CharacterStats(mind=2, hp=3),
            scripted_effects=("No proc; the value is in the unusual defensive caster profile and the story attached to it.",),
        ),
        tier=6,
    ),
    ItemDefinition(
        ONE_THIRD_CUP_KEY,
        "One-Third Cup",
        "The little measuring cup from the Deep Release Gate. No matter how carefully it is dried, one clear bead eventually appears in the bottom.",
        "curio",
        tier=6,
    ),
    ItemDefinition(LOCKMAKERS_MARGIN_KEY, "Lockmaker's Margin", "A narrow brass rubbing showing the Hill Warden's maintenance marks and a handwritten warning: NEVER REMOVE ALL LOAD AT ONCE.", "quest", tier=4),
    ItemDefinition(LAST_CARGO_MANIFEST_KEY, "Last Cargo Manifest", "The Glass Keel captain's final private manifest. The last listed cargo is not gold or spice but thirty-seven sealed water jars marked FOR SHORE WELLS.", "quest", tier=5),
    ItemDefinition(QUIET_GAUGE_KEY, "Quiet Gauge", "A tiny dead gauge removed from an abandoned Undertide inspection gallery. Its needle only moves when the main engine is silent.", "quest", tier=6),
)


# ---------------------------------------------------------------------------
# Three hidden rooms and three deliberately small side stories.
# ---------------------------------------------------------------------------
WARDEN_NICHE_KEY = "depth_warden_service_niche"
CAPTAINS_LOCKER_KEY = "depth_glass_keel_captains_locker"
UNDERTIDE_DRY_GALLERY_KEY = "depth_undertide_dry_gallery"

WARDEN_NICHE_FLAG = "depth_warden_niche_found"
CAPTAINS_LOCKER_FLAG = "depth_captains_locker_found"
DRY_GALLERY_FLAG = "depth_dry_gallery_found"

LOCKMAKER_QUEST_KEY = "depth_lockmakers_margin_quest"
LAST_CARGO_QUEST_KEY = "depth_last_cargo_quest"
QUIET_GAUGE_QUEST_KEY = "depth_quiet_gauge_quest"

LOCKMAKER_QUEST = QuestDefinition(
    key=LOCKMAKER_QUEST_KEY,
    name="The Lockmaker's Margin",
    style="freeform",
    minimum_level=18,
    description="A maintenance niche beside the Hill Warden contains evidence that its makers expected operators to redistribute load instead of simply destroying the guardian.",
    objective_steps=(("read_margin", "Find the hidden maintenance niche and READ MARGIN."), ("show_rook", "Return to the threshold and SHOW MARGIN TO ROOK."), ("complete", "Rook adds the old warning to the modern notes.")),
)
LAST_CARGO_QUEST = QuestDefinition(
    key=LAST_CARGO_QUEST_KEY,
    name="The Last Cargo",
    style="freeform",
    minimum_level=24,
    description="A private locker aboard the Glass Keel preserves the captain's final manifest, which may matter more to Keelspire than another piece of salvage.",
    objective_steps=(("take_manifest", "SEARCH BULKHEAD in the Captain's Round, then TAKE MANIFEST in the hidden locker."), ("show_orro", "SHOW MANIFEST TO ORRO on the Dry Quays."), ("complete", "Orro sends the record to the public archive instead of selling it.")),
)
QUIET_GAUGE_QUEST = QuestDefinition(
    key=QUIET_GAUGE_QUEST_KEY,
    name="The Gauge That Hates Noise",
    style="freeform",
    minimum_level=28,
    description="A dry inspection gallery beside the Undertide holds a gauge omitted from every surviving diagram.",
    objective_steps=(("take_gauge", "TRACE DRIP on the Pressure Walk, enter the hidden gallery, and TAKE GAUGE."), ("show_tavik", "SHOW GAUGE TO TAVIK in the Harbor Vault."), ("complete", "Tavik recognizes it as a shutdown-pressure instrument and adds the missing safety reading to the expedition notes.")),
)
SIDE_QUESTS = (LOCKMAKER_QUEST, LAST_CARGO_QUEST, QUIET_GAUGE_QUEST)

HIDDEN_ROOMS = (
    RoomDefinition(
        key=WARDEN_NICHE_KEY,
        name="Warden Service Niche",
        region_key="house_beneath_hill",
        description="A cramped maintenance recess sits behind the keeper masonry. Chalk marks show workers redistributing tension between the Warden's three locking bars one at a time. Someone underlined NEVER REMOVE ALL LOAD AT ONCE hard enough to score the brass.",
        exits={"south": HOUSE_KEEPER_LOCK_KEY},
        tags=("shared_world", "hidden", "side_story", "level_18_20"),
    ),
    RoomDefinition(
        key=CAPTAINS_LOCKER_KEY,
        name="Captain's Private Locker",
        region_key="salt_kingdoms_glass_keel",
        description="The compartment is barely large enough to kneel in. A private tideglass hangs in a padded bracket beside the captain's last cargo manifest. Nothing here was valuable enough for generations of salvagers to notice the false bulkhead.",
        exits={"west": GLASS_KEEL_CAPTAIN_KEY},
        tags=("shared_world", "salt_kingdoms", "hidden", "side_story", "level_24_25"),
    ),
    RoomDefinition(
        key=UNDERTIDE_DRY_GALLERY_KEY,
        name="Dry Inspection Gallery",
        region_key="salt_kingdoms_undertide",
        description="This narrow gallery is unnaturally dry. One tiny gauge has been isolated from the engine by layers of cork and felt so it can measure what the system does only when the great pipes stop vibrating.",
        exits={"north": UNDERTIDE_PRESSURE_WALK_KEY},
        tags=("shared_world", "salt_kingdoms", "hidden", "side_story", "level_28_29"),
    ),
)


def _merge(existing: RoomAugmentation | None, extra: RoomAugmentation) -> RoomAugmentation:
    if existing is None:
        return extra
    extras = {(item.direction, item.destination_key): item for item in existing.extra_exits}
    extras.update({(item.direction, item.destination_key): item for item in extra.extra_exits})
    return replace(existing, extra_exits=tuple(extras.values()))


def depth_augmentations() -> dict[str, RoomAugmentation]:
    return {
        HOUSE_KEEPER_LOCK_KEY: RoomAugmentation(extra_exits=(
            ExitDefinition("north", WARDEN_NICHE_KEY, "Warden Service Niche", travel_text="You squeeze through the maintenance seam behind the keeper masonry.", condition=ViewCondition(required_flags=(WARDEN_NICHE_FLAG,)), hidden_when_unavailable=True),
        )),
        GLASS_KEEL_CAPTAIN_KEY: RoomAugmentation(extra_exits=(
            ExitDefinition("east", CAPTAINS_LOCKER_KEY, "False Bulkhead", travel_text="You slip through the sprung false bulkhead into the captain's private locker.", condition=ViewCondition(required_flags=(CAPTAINS_LOCKER_FLAG,)), hidden_when_unavailable=True),
        )),
        UNDERTIDE_PRESSURE_WALK_KEY: RoomAugmentation(extra_exits=(
            ExitDefinition("south", UNDERTIDE_DRY_GALLERY_KEY, "Dry Inspection Gallery", travel_text="You follow the impossible dry seam into an isolated inspection gallery.", condition=ViewCondition(required_flags=(DRY_GALLERY_FLAG,)), hidden_when_unavailable=True),
        )),
    }


def _replace_room(room: RoomDefinition) -> None:
    if room.key in legacy_world.ROOMS_BY_KEY:
        legacy_world.ROOMS = tuple(room if old.key == room.key else old for old in legacy_world.ROOMS)
    else:
        legacy_world.ROOMS = legacy_world.ROOMS + (room,)
    legacy_world.ROOMS_BY_KEY[room.key] = room


def install_midgame_depth_content(world_service=None) -> None:
    for item in NAMED_DEPTH_ITEMS:
        if item.key not in crafting.ITEMS_BY_KEY:
            crafting.ITEMS = crafting.ITEMS + (item,)
        crafting.ITEMS_BY_KEY[item.key] = item
    for quest in SIDE_QUESTS:
        if quest.key not in quests.QUESTS_BY_KEY:
            quests.QUESTS = quests.QUESTS + (quest,)
        quests.QUESTS_BY_KEY[quest.key] = quest
    for room in HIDDEN_ROOMS:
        _replace_room(room)
    if world_service is None:
        return
    for room in HIDDEN_ROOMS:
        world_service.legacy_rooms[room.key] = room
    for key, augmentation in depth_augmentations().items():
        world_service.augmentations[key] = _merge(world_service.augmentations.get(key), augmentation)
    cache = getattr(world_service, "_scene_cache", None)
    if cache is not None:
        for key in (*[room.key for room in HIDDEN_ROOMS], HOUSE_KEEPER_LOCK_KEY, GLASS_KEEL_CAPTAIN_KEY, UNDERTIDE_PRESSURE_WALK_KEY):
            cache.pop(key, None)


def _flags(session) -> set[str]:
    if session.character is None:
        return set()
    return set(session.database.list_flags(session.character.id))


def _quest(session, key: str):
    if session.character is None:
        return None
    return session.database.get_quest(session.character.id, key)


def _start_side(session, key: str, step: str) -> None:
    if session.character is not None and _quest(session, key) is None:
        session.database.start_quest(session.character.id, key, step)


def _give_once(session, key: str) -> bool:
    if session.character is None:
        return False
    if session.database.item_quantity(session.character.id, key) > 0:
        return False
    session.database.add_item(session.character.id, key, 1)
    return True


# First-clear boss mechanics. They are intentionally readable in text and require
# interaction with the room before the player can reduce the fight to raw stats.
WARDEN_BAR_FLAGS = ("depth_warden_left_bar", "depth_warden_right_bar")
MATRIARCH_FLAGS = ("depth_matriarch_port_weight", "depth_matriarch_starboard_weight")
REGENT_FLAGS = ("depth_regent_vent_east", "depth_regent_close_high", "depth_regent_open_return")


def _boss_ready(session, required: tuple[str, ...]) -> bool:
    flags = _flags(session)
    return all(flag in flags for flag in required)


async def _delegate(self, previous_playing_prompt, command: str) -> None:
    had = "prompt" in self.__dict__
    old = self.__dict__.get("prompt")

    async def replay(_text: str):
        return command

    self.prompt = replay
    try:
        await previous_playing_prompt(self)
    finally:
        if had:
            self.prompt = old
        else:
            self.__dict__.pop("prompt", None)


def install_midgame_depth_runtime(player_session_class, world_service) -> None:
    install_midgame_depth_content(world_service)
    if getattr(player_session_class, "_midgame_depth_installed", False):
        return

    previous_playing_prompt = player_session_class.playing_prompt
    previous_finish_enemy = player_session_class._finish_enemy_defeat

    async def _finish_enemy_defeat(self, enemy) -> None:
        key = enemy.definition.key
        eligible = getattr(self, "active_enemy", None) is enemy
        await previous_finish_enemy(self, enemy)
        if not eligible or self.character is None:
            return
        reward = {
            HILL_WARDEN_KEY: (WARDENS_IRON_KEY, "Among the broken locking plates you recover Warden's Iron."),
            BALLAST_MATRIARCH_KEY: (BRINEGLASS_KNIFE_KEY, "Inside the shattered shell nest you recover a sharpened Brineglass Knife."),
            SLUICE_REGENT_KEY: (REGENT_VALVE_CROWN_KEY, "The Regent's pressure-vane crown comes free intact: Sluice Regent's Valve-Crown."),
        }.get(key)
        if reward and _give_once(self, reward[0]):
            await self.send(reward[1] + "\r\n")

    async def playing_prompt(self) -> None:
        if self.character is None:
            await previous_playing_prompt(self)
            return
        command = await self.prompt("\r\n> ")
        if command is None:
            self.state = type(self.state).DISCONNECTED
            return
        n = " ".join(command.strip().lower().split())
        room = self.character.current_room

        # Hill Warden: redistribute two locking bars before committing to the kill.
        if room == HOUSE_KEEPER_LOCK_KEY and n in {"break left bar", "release left bar", "loosen left bar"}:
            self.database.grant_flag(self.character.id, WARDEN_BAR_FLAGS[0])
            await self.send("You release the left locking bar a notch at a time. The Warden turns toward the changing load instead of simply attacking. One side of the chamber stops screaming under tension.\r\n")
            return
        if room == HOUSE_KEEPER_LOCK_KEY and n in {"break right bar", "release right bar", "loosen right bar"}:
            self.database.grant_flag(self.character.id, WARDEN_BAR_FLAGS[1])
            await self.send("You walk the right locking bar out of its seat in controlled increments. The floor settles. The Warden is now carrying its own weight instead of the whole hill's.\r\n")
            return
        if room == HOUSE_KEEPER_LOCK_KEY and ("warden" in n) and (n.startswith("attack ") or n.startswith("kill ")) and not _boss_ready(self, WARDEN_BAR_FLAGS):
            await self.send("The Warden is still hard-linked to the hill. Raw attacks make the locking bars pull against the whole chamber. RELEASE LEFT BAR and RELEASE RIGHT BAR first.\r\n")
            return

        # Ballast Matriarch: stabilize the tilted ship by countering both weight lines.
        if room == GLASS_KEEL_BALLAST_KEY and n in {"cut port weight", "release port weight", "shift port ballast"}:
            self.database.grant_flag(self.character.id, MATRIARCH_FLAGS[0])
            await self.send("The port ballast crashes one deck lower. The Glass Keel rolls several inches and the Matriarch scrambles to keep its nest from sliding.\r\n")
            return
        if room == GLASS_KEEL_BALLAST_KEY and n in {"cut starboard weight", "release starboard weight", "shift starboard ballast"}:
            self.database.grant_flag(self.character.id, MATRIARCH_FLAGS[1])
            await self.send("The starboard counterweight drops. The tilted deck stops trying to throw you toward the shell nest.\r\n")
            return
        if room == GLASS_KEEL_BALLAST_KEY and ("matriarch" in n or "crab" in n) and (n.startswith("attack ") or n.startswith("kill ")) and not _boss_ready(self, MATRIARCH_FLAGS):
            await self.send("The Matriarch owns the angle of the room; every rush becomes a slide toward its claws. CUT PORT WEIGHT and CUT STARBOARD WEIGHT to stabilize the fighting surface.\r\n")
            return

        # Sluice Regent: a readable three-control pressure sequence creates the safe opening.
        if room == UNDERTIDE_REGENT_KEY and n in {"vent east", "open east vent"}:
            self.database.grant_flag(self.character.id, REGENT_FLAGS[0])
            await self.send("The east relief line vents. The Regent immediately gives up one arm to compensate elsewhere.\r\n")
            return
        if room == UNDERTIDE_REGENT_KEY and n in {"close high", "close high line", "shut high line"}:
            if REGENT_FLAGS[0] not in _flags(self):
                await self.send("The high line is carrying too much pressure to close safely. VENT EAST first.\r\n")
                return
            self.database.grant_flag(self.character.id, REGENT_FLAGS[1])
            await self.send("You close the high-pressure bypass. The Regent pivots, exposing the vane-crown while it catches the load with two lower arms.\r\n")
            return
        if room == UNDERTIDE_REGENT_KEY and n in {"open return", "open return line", "release return"}:
            if not all(flag in _flags(self) for flag in REGENT_FLAGS[:2]):
                await self.send("The return line would hammer shut under current pressure. VENT EAST, then CLOSE HIGH first.\r\n")
                return
            self.database.grant_flag(self.character.id, REGENT_FLAGS[2])
            await self.send("The return line opens. Pressure equalizes across Regent Court and the guardian finally has to fight you instead of the entire engine at once.\r\n")
            return
        if room == UNDERTIDE_REGENT_KEY and ("regent" in n) and (n.startswith("attack ") or n.startswith("kill ")) and not _boss_ready(self, REGENT_FLAGS):
            await self.send("The Regent is using live water pressure as armor. Read the floor diagram: VENT EAST, CLOSE HIGH, OPEN RETURN.\r\n")
            return

        # Hidden room discoveries and side stories.
        if room == HOUSE_KEEPER_LOCK_KEY and n in {"search masonry", "search wall", "follow cable", "trace cable"}:
            self.database.grant_flag(self.character.id, WARDEN_NICHE_FLAG)
            _start_side(self, LOCKMAKER_QUEST_KEY, "read_margin")
            await self.send("Behind a soot-black cable chase you find a human-width maintenance seam. A hidden NORTH exit now leads to the Warden Service Niche.\r\n")
            return
        if room == WARDEN_NICHE_KEY and n in {"read margin", "read warning", "examine brass", "read brass"}:
            _start_side(self, LOCKMAKER_QUEST_KEY, "read_margin")
            q = _quest(self, LOCKMAKER_QUEST_KEY)
            if q and q["status"] == "active" and q["current_step"] == "read_margin":
                _give_once(self, LOCKMAKERS_MARGIN_KEY)
                self.database.advance_quest(self.character.id, LOCKMAKER_QUEST_KEY, "show_rook")
            await self.send("The old maintenance margin is brutally practical: the Warden was designed to have load moved off one bar at a time. Somebody added, NEVER REMOVE ALL LOAD AT ONCE. You take a brass rubbing.\r\n")
            return
        if room == HOUSE_THRESHOLD_KEY and n in {"show margin to rook", "show rook margin", "give margin rook"}:
            q = _quest(self, LOCKMAKER_QUEST_KEY)
            if q and q["status"] == "active" and q["current_step"] == "show_rook":
                self.database.complete_quest(self.character.id, LOCKMAKER_QUEST_KEY)
                self.database.add_experience(self.character.id, 500)
                await self.send("Rook reads the rubbing twice. 'Good. That goes in the notes before somebody calls bravery what was actually bad maintenance.' Side story complete: The Lockmaker's Margin. +500 XP.\r\n")
                return

        if room == GLASS_KEEL_CAPTAIN_KEY and n in {"search bulkhead", "search wall", "tap bulkhead", "examine bulkhead"}:
            self.database.grant_flag(self.character.id, CAPTAINS_LOCKER_FLAG)
            _start_side(self, LAST_CARGO_QUEST_KEY, "take_manifest")
            await self.send("One bulkhead answers with the wrong hollow note. Its salt seam breaks under your fingers, revealing a hidden EAST passage into the captain's private locker.\r\n")
            return
        if room == CAPTAINS_LOCKER_KEY and n in {"take manifest", "read manifest", "take cargo manifest"}:
            _start_side(self, LAST_CARGO_QUEST_KEY, "take_manifest")
            _give_once(self, LAST_CARGO_MANIFEST_KEY)
            q = _quest(self, LAST_CARGO_QUEST_KEY)
            if q and q["status"] == "active" and q["current_step"] == "take_manifest":
                self.database.advance_quest(self.character.id, LAST_CARGO_QUEST_KEY, "show_orro")
            await self.send("The final cargo entry is thirty-seven sealed water jars marked FOR SHORE WELLS. You take the manifest rather than stripping its copper fittings.\r\n")
            return
        if room == CAPTAINS_LOCKER_KEY and n in {"take tideglass", "take glass", "remove tideglass"}:
            if _give_once(self, CAPTAINS_TIDEGLASS_KEY):
                await self.send("You lift the Captain's Tideglass from its padded bracket. The sealed liquid makes one tiny correction toward the ship's keel.\r\n")
            else:
                await self.send("The tideglass bracket is already empty.\r\n")
            return
        if room == KEELSPIRE_QUAYS_KEY and n in {"show manifest to orro", "show orro manifest", "give manifest orro"}:
            q = _quest(self, LAST_CARGO_QUEST_KEY)
            if q and q["status"] == "active" and q["current_step"] == "show_orro":
                self.database.complete_quest(self.character.id, LAST_CARGO_QUEST_KEY)
                self.database.add_experience(self.character.id, 700)
                await self.send("Orro whistles at the last line. 'Water jars for shore wells. Captain knew the coast was thirsty before the sea finished leaving.' He sends a copy to the Basin Archive instead of pricing it. Side story complete: The Last Cargo. +700 XP.\r\n")
                return

        if room == UNDERTIDE_PRESSURE_WALK_KEY and n in {"trace drip", "follow drip", "search dry seam", "listen wall"}:
            self.database.grant_flag(self.character.id, DRY_GALLERY_FLAG)
            _start_side(self, QUIET_GAUGE_QUEST_KEY, "take_gauge")
            await self.send("A single drip runs uphill and vanishes beneath a felted seam. Behind it is a hidden SOUTH passage into a vibration-isolated gallery.\r\n")
            return
        if room == UNDERTIDE_DRY_GALLERY_KEY and n in {"take gauge", "remove gauge", "examine gauge"}:
            _start_side(self, QUIET_GAUGE_QUEST_KEY, "take_gauge")
            _give_once(self, QUIET_GAUGE_KEY)
            q = _quest(self, QUIET_GAUGE_QUEST_KEY)
            if q and q["status"] == "active" and q["current_step"] == "take_gauge":
                self.database.advance_quest(self.character.id, QUIET_GAUGE_QUEST_KEY, "show_tavik")
            await self.send("The tiny gauge is isolated from vibration on purpose. Its face reads SHUTDOWN DIFFERENTIAL. You take it carefully.\r\n")
            return
        if room == KEELSPIRE_HARBOR_VAULT_KEY and n in {"show gauge to tavik", "show tavik gauge", "give gauge tavik"}:
            q = _quest(self, QUIET_GAUGE_QUEST_KEY)
            if q and q["status"] == "active" and q["current_step"] == "show_tavik":
                self.database.complete_quest(self.character.id, QUIET_GAUGE_QUEST_KEY)
                self.database.add_experience(self.character.id, 900)
                await self.send("Tavik goes quiet. 'This only reads when the big system is off. That's why every running survey missed it.' He adds a shutdown-pressure column to the expedition ledger. Side story complete: The Gauge That Hates Noise. +900 XP.\r\n")
                return

        if room == UNDERTIDE_RELEASE_KEY and n in {"take cup", "take measuring cup", "pick up cup"}:
            if ODDITY_CUP_FLAG not in _flags(self):
                await self.send("The little cup looks ordinary enough. Something about it suggests watching before taking.\r\n")
            elif _give_once(self, ONE_THIRD_CUP_KEY):
                await self.send("You take the One-Third Cup. A clear bead forms in it almost immediately.\r\n")
            else:
                await self.send("You already carry the One-Third Cup.\r\n")
            return

        await _delegate(self, previous_playing_prompt, command)

    player_session_class.playing_prompt = playing_prompt
    player_session_class._finish_enemy_defeat = _finish_enemy_defeat
    player_session_class._midgame_depth_installed = True
