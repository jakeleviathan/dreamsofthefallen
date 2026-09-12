from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass

import mud.combat as combat
import mud.crafting as crafting
import mud.economy_loop as economy
import mud.quests as quests
import mud.trade_experience as trade_experience
import mud.world as legacy_world
from mud.astralis_time import ASTRALIS_CLOCK
from mud.combat import EnemyDefinition, EnemyState
from mud.content_foundry import DUNGEONS as FOUNDRY_DUNGEONS
from mud.content_foundry import GLASSFRUIT_SHARD, ASHWHEEL_SPOKE, NINTH_VAPOR_RESIN
from mud.crafting import ItemDefinition
from mud.gear import CraftingRecipe, MaterialRequirement
from mud.greywake_march import GREYWAKE_WEST_MILE_KEY, GREYWAKE_RIFTFIELD_KEY
from mud.iconic_items import ICONIC_BY_KEY
from mud.living_world import _chronicle_insert
from mud.quests import QuestDefinition
from mud.room_engine import FeatureDefinition, RoomAugmentation
from mud.sablewater_reach import (
    SABLEWATER_DRIFTWOOD_SHRINE_KEY,
    SABLEWATER_EEL_DOCK_KEY,
    SABLEWATER_ROOKERY_KEY,
)
from mud.stats import CharacterStats, EquipmentItem
from mud.veyra_city import (
    VEYRA_BRASSMARKET_KEY,
    VEYRA_EAST_RIVER_GATE_KEY,
    VEYRA_OLD_BRIDGE_KEY,
    VEYRA_SCHOLARS_RISE_KEY,
)
from mud.waymeet_frontier import WAYMEET_BRIARCUT_KEY, WAYMEET_LANTERN_MARKET_KEY
from mud.world import RoomDefinition


DENSITY_VERSION = "1.0.0"


@dataclass(frozen=True, slots=True)
class DungeonSeed:
    key: str
    name: str
    anchor: str
    level_band: tuple[int, int]
    mechanic_command: str
    mechanic_text: str
    mob_name: str
    miniboss_name: str
    boss_name: str
    iconic_drop: str


DUNGEON_SEEDS = (
    DungeonSeed("small_saint", "Chapel of the Small Saint", WAYMEET_BRIARCUT_KEY, (4, 6), "LIGHT LAST WICK", "The chapel answers only after the smallest surviving wick is lit.", "Ash Pilgrim", "The Unshriven Sexton", "Saintless Keeper", "saint_small_fires_lantern"),
    DungeonSeed("salt_king", "Salt-King's Larder", SABLEWATER_DRIFTWOOD_SHRINE_KEY, (6, 8), "DRAIN THIRD VAT", "Three brine vats feed the lower pantry; only the third still drains toward the river.", "Brine Gnawer", "The Pickled Steward", "The Salt King", "dry_boots_sablewater"),
    DungeonSeed("red_door", "Red Door Cellars", VEYRA_OLD_BRIDGE_KEY, (7, 9), "TURN RED KEY", "A red keyhole is set into a door that is otherwise entirely black.", "Velvet Rat", "The Velvet Locksmith", "Red Door Custodian", "key_to_red_door"),
    DungeonSeed("broken_observatory", "Broken Observatory", VEYRA_SCHOLARS_RISE_KEY, (8, 10), "ALIGN FALLEN LENS", "The fallen lens still tracks something above the visible sky if its cracked marks are aligned.", "Starblind Mite", "The Blind Astrolabe", "Watcher of the Fallen Moon", "moon_that_fell_helm"),
    DungeonSeed("rootcourt", "Rootcourt Warrens", GREYWAKE_RIFTFIELD_KEY, (7, 10), "KNOCK ROOT THREE", "Three hollow roots answer at different pitches; the third answers from somewhere deeper.", "Rootcourt Burrower", "Hollow Antler", "The Rootcourt Queen", "last_green_leaf"),
    DungeonSeed("brass_lung", "Brass Lung Foundry", VEYRA_EAST_RIVER_GATE_KEY, (9, 11), "VENT LEFT LUNG", "The foundry breathes through paired pressure lungs. The left one is overfull and visibly shaking.", "Soot Riveter", "Foreman Bellows", "Furnace Breath", "gauge_zero"),
    DungeonSeed("white_room", "White Room Annex", GREYWAKE_WEST_MILE_KEY, (10, 12), "SIT EMPTY CHAIR", "One white chair faces a blank wall. Every footprint in the room stops before it.", "Pale Attendant", "The Chair Without Guest", "The White Curator", "word_that_wasnt_spoken"),
)
assert len(FOUNDRY_DUNGEONS) + len(DUNGEON_SEEDS) == 10


# Each new dungeon contributes two reliable boss materials. The first belongs to
# the miniboss; the second is the signature ingredient from the final encounter.
BOSS_MATERIAL_ITEMS: list[ItemDefinition] = []
for seed in DUNGEON_SEEDS:
    BOSS_MATERIAL_ITEMS.extend((
        ItemDefinition(f"density_{seed.key}_minor_material", f"{seed.miniboss_name} Remnant", f"A useful remnant recovered from {seed.miniboss_name}; artisans value it because its origin is unmistakable.", "material", tier=3),
        ItemDefinition(f"density_{seed.key}_major_material", f"{seed.boss_name} Relic Material", f"A reliable crafting material recovered after defeating {seed.boss_name}. It carries the material language of {seed.name}.", "material", tier=4),
    ))
BOSS_MATERIAL_ITEMS = tuple(BOSS_MATERIAL_ITEMS)


# One hundred ordinary, named pieces. These are intentionally not all jackpots:
# they make shops, corpses, crafts and trades feel full between the legendary hits.
GEAR_FAMILIES = (
    ("waymeet", "Waymeet Road", 1),
    ("greywake", "Greywake March", 2),
    ("veyra", "Veyra Civic", 2),
    ("sablewater", "Sablewater Reed", 2),
    ("blackreed", "Blackreed Reclaimed", 2),
    ("gravewatch", "Gravewatch Iron", 3),
    ("underclock", "Underclock Work", 3),
    ("glass_orchard", "Glass Orchard", 3),
    ("ash_relay", "Ash Relay", 3),
    ("nine_vapors", "Nine Vapors", 3),
)
GEAR_PATTERNS = (
    ("cap", "Cap", "head"),
    ("coat", "Coat", "chest"),
    ("greaves", "Greaves", "legs"),
    ("boots", "Boots", "feet"),
    ("gloves", "Gloves", "hands"),
    ("shortblade", "Shortblade", "main_hand"),
    ("longblade", "Longblade", "main_hand"),
    ("buckler", "Buckler", "off_hand"),
    ("staff", "Field Staff", "main_hand"),
    ("targe", "Targe", "off_hand"),
)


def _ordinary_gear() -> tuple[ItemDefinition, ...]:
    result = []
    for family_index, (family_key, family_name, tier) in enumerate(GEAR_FAMILIES):
        for pattern_index, (pattern_key, pattern_name, slot) in enumerate(GEAR_PATTERNS):
            name = f"{family_name} {pattern_name}"
            is_weapon = slot == "main_hand"
            is_armor = slot in {"head", "chest", "legs", "feet", "hands", "off_hand"}
            stats = CharacterStats(
                might=tier if is_weapon and pattern_index % 2 == 0 else 0,
                grace=1 if pattern_key in {"boots", "shortblade"} else 0,
                love=1 if pattern_key == "staff" and family_index % 2 == 0 else 0,
                mind=1 if pattern_key == "staff" and family_index % 2 == 1 else 0,
                hp=tier if pattern_key == "coat" else 0,
            )
            result.append(ItemDefinition(
                f"density_gear_{family_key}_{pattern_key}",
                name,
                f"A practical {pattern_name.lower()} made in the {family_name} tradition. It is useful, recognizable, and meant to live in the economy rather than wait for a perfect build.",
                "equipment",
                equipment=EquipmentItem(name, slot, armor_class=tier if is_armor else 0, stat_bonuses=stats),
                tier=tier,
            ))
    return tuple(result)


EVERYDAY_GEAR = _ordinary_gear()
assert len(EVERYDAY_GEAR) == 100


CURIO_NAMES = (
    "Bottle of Rain That Smells Like Dust", "Tiny Brass Horse With One Wheel", "Perfume Sample: Violet Static",
    "Perfume Sample: Wet Book", "Perfume Sample: Green Bell", "Perfume Sample: Cold Pear",
    "Half of a Goblin Apology Token", "White Button From an Unknown Uniform", "Glass Marble With a Moving Bubble",
    "Toy Underclock With Seven Teeth", "Bent Veyra Tram Ticket", "Pressed Heron Feather in Wax",
    "Miniature Blackwall Gargoyle", "Unsigned Funeral Invitation", "Sporekin Story Pebble",
    "Moon Elf Pocket Horizon", "Dwarf Union Tea Chit", "Troll Bone Dice Pair",
    "Forest Elf Seed Packet Marked DO NOT PLANT", "Undead Birthday Candle", "Little Red Door With No Hinge",
    "Three-Banner Argument Card", "Perfume Sample: Lantern Smoke", "Perfume Sample: Silver Onion",
    "Perfume Sample: After the Storm", "Ash Driver Toy Coach", "Salt-King Pickle Fork",
    "Rootcourt Wooden Crown", "White Room Pencil", "Receipt for One Impossible Chair",
)
CURIOS = tuple(
    ItemDefinition(f"density_curio_{i:02d}", name, f"{name}. It has no combat value; its purpose is memory, trade, display, jokes, and the possibility that somebody else knows more about it than you do.", "trophy", tier=1 + i // 10)
    for i, name in enumerate(CURIO_NAMES, 1)
)
assert len(CURIOS) == 30


# Forty recipes: four per material family. Each crosses at least one regional
# boundary rather than letting a dungeon consume only its own output.
RECIPE_MATERIALS = (
    GLASSFRUIT_SHARD, ASHWHEEL_SPOKE, NINTH_VAPOR_RESIN,
    "density_small_saint_major_material", "density_salt_king_major_material", "density_red_door_major_material",
    "density_broken_observatory_major_material", "density_rootcourt_major_material", "density_brass_lung_major_material",
    "density_white_room_major_material",
)
BASE_CROSS_MATERIALS = ("iron_ingot", "cotton_cloth", "steel_ingot", "wool_cloth", "rough_hide", "silk_cloth", "coal", "moonweave_cloth", "drowned_brass_scrap", "lavender_blossom")


def _recipes() -> tuple[CraftingRecipe, ...]:
    recipes = []
    for family_index, (family_key, _family_name, _tier) in enumerate(GEAR_FAMILIES):
        outputs = EVERYDAY_GEAR[family_index * 10: family_index * 10 + 4]
        local = RECIPE_MATERIALS[family_index]
        cross = BASE_CROSS_MATERIALS[(family_index + 3) % len(BASE_CROSS_MATERIALS)]
        for i, output in enumerate(outputs):
            trade = "blacksmithing" if i in {0, 2} else "tailoring"
            station = "forge" if trade == "blacksmithing" else "loom"
            recipes.append(CraftingRecipe(
                f"density_make_{family_key}_{i}", trade, output.key,
                8 + family_index * 4 + i, 30 + family_index * 4 + i,
                (MaterialRequirement(local, 1), MaterialRequirement(cross, 1)),
                station_key=station,
                description=f"A cross-road recipe combining {local.replace('_', ' ')} with material normally sourced elsewhere in Astralis.",
                design_status="astralis_density",
            ))
    return tuple(recipes)


DENSITY_RECIPES = _recipes()
assert len(DENSITY_RECIPES) == 40


# Seven six-room dungeons. Together with the three content-foundry delves, this
# makes the promised ten-dungeon expansion.
def _build_rooms(seed: DungeonSeed) -> tuple[RoomDefinition, ...]:
    keys = tuple(f"density_{seed.key}_{i}" for i in range(1, 7))
    mob_key = f"density_{seed.key}_mob"
    mini_key = f"density_{seed.key}_miniboss"
    boss_key = f"density_{seed.key}_boss"
    descriptions = (
        f"The threshold of {seed.name} feels used rather than staged. Scuffs, discarded tools, and old repairs show that ordinary people once had reasons to come here.",
        f"A working passage inside {seed.name} has become dangerous in a very local way; nothing here suggests the world is ending, only that this place has gone wrong.",
        f"The route narrows into a defended chamber. {seed.miniboss_name} has made this part of the ruin its own.",
        f"The dungeon finally explains its trick in physical terms. {seed.mechanic_text} The useful command is written into the scene: {seed.mechanic_command}.",
        f"Beyond the solved mechanism, the final approach to {seed.boss_name} is strangely calm. This is the last place to prepare before the room stops being forgiving.",
        f"The heart of {seed.name}. {seed.boss_name} waits among the objects and damage that made the place famous.",
    )
    result = []
    for i, key in enumerate(keys):
        exits = {}
        if i > 0:
            exits["west"] = keys[i - 1]
        if i < 3:
            exits["east"] = keys[i + 1]
        if i == 4:
            exits["east"] = keys[5]
        enemies = (mob_key,) if i in {0, 1} else (mini_key,) if i == 2 else (boss_key,) if i == 5 else ()
        result.append(RoomDefinition(key, f"{seed.name}: {('Threshold','Working Passage','Keeper Chamber','Mechanism Hall','Final Approach','Heart')[i]}", descriptions[i], f"density_{seed.key}", exits, enemy_keys=enemies, tags=("shared_world", "dungeon", "density", f"level_{seed.level_band[0]}_{seed.level_band[1]}")))
    return tuple(result)


DENSITY_ROOMS = tuple(room for seed in DUNGEON_SEEDS for room in _build_rooms(seed))
assert len(DENSITY_ROOMS) == 42
DUNGEON_ROOM_KEYS = {seed.key: tuple(f"density_{seed.key}_{i}" for i in range(1, 7)) for seed in DUNGEON_SEEDS}


def _build_dungeon_enemies() -> tuple[EnemyDefinition, ...]:
    result = []
    for i, seed in enumerate(DUNGEON_SEEDS):
        base = 78 + i * 12
        result.extend((
            EnemyDefinition(f"density_{seed.key}_mob", seed.mob_name, (seed.mob_name.lower(), "denizen"), f"a characteristic denizen of {seed.name}, dangerous because it belongs here and knows the ground", base, 8 + i, 7 + i, 3.0, 48 + i * 8),
            EnemyDefinition(f"density_{seed.key}_miniboss", seed.miniboss_name, (seed.miniboss_name.lower(), "keeper"), f"{seed.miniboss_name}, a local power that teaches the dungeon's tone before the final chamber", base + 90, 12 + i, 10 + i, 3.0, 110 + i * 12),
            EnemyDefinition(f"density_{seed.key}_boss", seed.boss_name, (seed.boss_name.lower(), "boss"), f"{seed.boss_name}, the figure players will remember when they remember {seed.name}", base + 220, 15 + i, 13 + i, 2.9, 220 + i * 18),
        ))
    return tuple(result)


DUNGEON_ENEMIES = _build_dungeon_enemies()
MINIBOSS_KEYS = {f"density_{seed.key}_miniboss" for seed in DUNGEON_SEEDS}
FINAL_BOSS_KEYS = {f"density_{seed.key}_boss" for seed in DUNGEON_SEEDS}


# Three wandering world bosses bring the density wave to twenty memorable boss
# encounters when combined with the 14 dungeon bosses and the foundry's 3 finals.
WORLD_BOSSES = (
    EnemyDefinition("density_night_tailor", "The Night Tailor", ("night tailor", "tailor"), "a perfectly dressed traveler carrying black shears and a measuring cord that never touches the ground", 390, 19, 17, 2.8, 340),
    EnemyDefinition("density_countryless_king", "The King Without a Country", ("countryless king", "king"), "a crowned wanderer with no heraldry, no escort, and the exhausted posture of someone still ruling something nobody can find", 430, 20, 18, 3.0, 370),
    EnemyDefinition("density_lonely_chorus", "The Lonely Chorus", ("lonely chorus", "chorus"), "a vast pale fungal figure whose spores drift away from one another instead of joining", 410, 18, 17, 2.9, 360),
)
WORLD_BOSS_ICONICS = {
    "density_night_tailor": "thirteen_button_coat",
    "density_countryless_king": "king_without_country_crown",
    "density_lonely_chorus": "lonely_cap_helm",
}
assert len(MINIBOSS_KEYS) + len(FINAL_BOSS_KEYS) + len(WORLD_BOSSES) + len(FOUNDRY_DUNGEONS) == 20


# Thirty-four rare creatures supplement the foundry's Silverhart and Rainthread
# Serpent, yielding 36 rare-world creatures in the overall content pass.
_RARE_ADJ = ("Copper", "Moss", "Moon", "Ash", "Reed", "Glass", "Hollow", "White", "Black", "Violet", "Rust", "Silver", "Soot", "Rain", "Root", "Bell", "Salt")
_RARE_NOUN = ("Marten", "Hare")
RARE_HOSTS = (
    WAYMEET_BRIARCUT_KEY, WAYMEET_LANTERN_MARKET_KEY, GREYWAKE_WEST_MILE_KEY, GREYWAKE_RIFTFIELD_KEY,
    VEYRA_OLD_BRIDGE_KEY, VEYRA_SCHOLARS_RISE_KEY, VEYRA_EAST_RIVER_GATE_KEY, VEYRA_BRASSMARKET_KEY,
    SABLEWATER_DRIFTWOOD_SHRINE_KEY, SABLEWATER_EEL_DOCK_KEY, SABLEWATER_ROOKERY_KEY,
)
RARE_CREATURES = tuple(
    EnemyDefinition(f"density_rare_{i:02d}", f"{adj}{noun}", (f"{adj.lower()}{noun.lower()}", noun.lower()), f"an uncommon {noun.lower()} marked by a strange {adj.lower()} coloration or behavior; the sort of creature travelers argue about after seeing once", 90 + i * 3, 8 + i % 6, 7 + i % 6, 2.8 + (i % 3) * 0.1, 55 + i * 3)
    for i, (adj, noun) in enumerate(((a, n) for a in _RARE_ADJ for n in _RARE_NOUN), 1)
)
assert len(RARE_CREATURES) == 34
RARE_HOST_BY_KEY = {creature.key: RARE_HOSTS[i % len(RARE_HOSTS)] for i, creature in enumerate(RARE_CREATURES)}


# Twenty tiny errands. They are deliberately small, local and a little odd.
ODDJOB_NAMES = (
    "Return the Blue Cup", "Count the Unmatched Boots", "Deliver a Quiet Letter", "Find the Missing Ladle", "Check the Third Milepost",
    "Bring Back a White Feather", "Ask Who Owns the Red Umbrella", "Carry a Broken Clock Hand", "Take Soup to the Ferryman", "Confirm the Door Is Still Green",
    "Borrow a Dwarf's Pencil", "Return a Goblin Screw", "Measure the Crooked Bench", "Tell the Keeper It Rained", "Find a Clean Piece of String",
    "Carry the Empty Bottle", "Ask the Rooks Nothing", "Check the Bridge Hum", "Bring Back One Ordinary Stone", "Leave the Chair Alone",
)
ODDJOB_STARTS = tuple(RARE_HOSTS[i % len(RARE_HOSTS)] for i in range(20))
ODDJOB_DESTS = tuple(RARE_HOSTS[(i + 3) % len(RARE_HOSTS)] for i in range(20))
ODDJOBS = tuple(
    QuestDefinition(
        key=f"density_oddjob_{i:02d}", name=name, style="discovery", minimum_level=2,
        description=f"A tiny piece of local life: {name.lower()}. It is intentionally smaller than an adventure and may end with more personality than reward.",
        objective_steps=(("travel", f"Carry the errand to {ODDJOB_DESTS[i - 1].replace('_', ' ')} and use FINISH ODDJOB."), ("complete", "The errand is finished.")),
    )
    for i, name in enumerate(ODDJOB_NAMES, 1)
)
assert len(ODDJOBS) == 20


ALL_DENSITY_ITEMS = BOSS_MATERIAL_ITEMS + EVERYDAY_GEAR + CURIOS
ALL_DENSITY_ENEMIES = DUNGEON_ENEMIES + WORLD_BOSSES + RARE_CREATURES
BOSS_KEYS = MINIBOSS_KEYS | FINAL_BOSS_KEYS | {boss.key for boss in WORLD_BOSSES}


def _register_recipe(recipe: CraftingRecipe) -> None:
    if recipe.key in crafting.RECIPES_BY_KEY:
        return
    crafting.ALL_RECIPES = crafting.ALL_RECIPES + (recipe,)
    crafting.RECIPES_BY_KEY[recipe.key] = recipe
    if recipe.trade_skill_key == "blacksmithing":
        crafting.BLACKSMITHING_RECIPES = crafting.BLACKSMITHING_RECIPES + (recipe,)
        crafting.BLACKSMITHING_RECIPES_BY_KEY[recipe.key] = recipe
    elif recipe.trade_skill_key == "tailoring":
        crafting.TAILORING_RECIPES = crafting.TAILORING_RECIPES + (recipe,)
        crafting.TAILORING_RECIPES_BY_KEY[recipe.key] = recipe


def _merge_aug(existing, extra):
    if existing is None:
        return extra
    return RoomAugmentation(
        exit_overrides=existing.exit_overrides + extra.exit_overrides,
        extra_exits=existing.extra_exits + extra.extra_exits,
        features=existing.features + extra.features,
        description_layers=existing.description_layers + extra.description_layers,
    )


def install_density_content(world_service) -> None:
    additions = []
    for item in ALL_DENSITY_ITEMS:
        if item.key not in crafting.ITEMS_BY_KEY:
            additions.append(item)
            crafting.ITEMS_BY_KEY[item.key] = item
    if additions:
        crafting.ITEMS = crafting.ITEMS + tuple(additions)
    for recipe in DENSITY_RECIPES:
        _register_recipe(recipe)
    for enemy in ALL_DENSITY_ENEMIES:
        if enemy.key not in combat.ENEMIES_BY_KEY:
            combat.ENEMIES = combat.ENEMIES + (enemy,)
        combat.ENEMIES_BY_KEY[enemy.key] = enemy
    for room in DENSITY_ROOMS:
        legacy_world.ROOMS_BY_KEY[room.key] = room
        if not any(r.key == room.key for r in legacy_world.ROOMS):
            legacy_world.ROOMS = legacy_world.ROOMS + (room,)
        world_service.legacy_rooms[room.key] = room
    for quest in ODDJOBS:
        if quest.key not in quests.QUESTS_BY_KEY:
            quests.QUESTS = quests.QUESTS + (quest,)
        quests.QUESTS_BY_KEY[quest.key] = quest

    # Reliable boss materials make repeat clears useful even when the rare flex
    # item does not appear.
    for seed in DUNGEON_SEEDS:
        economy.LOOT_TABLES[f"density_{seed.key}_miniboss"] = (economy.LootDrop(f"density_{seed.key}_minor_material", 1),)
        economy.LOOT_TABLES[f"density_{seed.key}_boss"] = (economy.LootDrop(f"density_{seed.key}_major_material", 1),)
    for i, boss in enumerate(WORLD_BOSSES):
        economy.LOOT_TABLES[boss.key] = (economy.LootDrop(CURIOS[i].key, 1),)
    for i, rare in enumerate(RARE_CREATURES):
        economy.LOOT_TABLES[rare.key] = (economy.LootDrop(CURIOS[(i + 3) % len(CURIOS)].key, 1),)

    # Entrance features point to verbs instead of hiding parser guesses.
    for seed in DUNGEON_SEEDS:
        feature = FeatureDefinition(
            f"density_entrance_{seed.key}", seed.name,
            aliases=(seed.key.replace("_", " "), "entrance", "delve"),
            summary=f"signs of an explorable place: {seed.name}",
            examine_text=f"The route is usable. ENTER {seed.name.upper()} to descend or step inside; RETREAT returns to the entrance road.",
        )
        world_service.augmentations[seed.anchor] = _merge_aug(world_service.augmentations.get(seed.anchor), RoomAugmentation(features=(feature,)))
    cache = getattr(world_service, "_scene_cache", None)
    if cache is not None:
        for key in (*RARE_HOSTS, *(seed.anchor for seed in DUNGEON_SEEDS), *(room.key for room in DENSITY_ROOMS)):
            cache.pop(key, None)


def _normalize(text: str) -> str:
    return " ".join(text.strip().lower().replace("_", " ").split())


def _refresh_character(session) -> None:
    if session.character is None:
        return
    refreshed = session.database.get_character_by_name(session.character.name)
    if refreshed is not None:
        session.character = refreshed


def _resolve_owned_item(session, target: str) -> str | None:
    if session.character is None:
        return None
    wanted = _normalize(target)
    exact = []
    partial = []
    for row in session.database.list_items(session.character.id):
        key = str(row["item_key"])
        item = crafting.ITEMS_BY_KEY.get(key)
        if item is None:
            continue
        names = {_normalize(key), _normalize(item.name)}
        if wanted in names:
            exact.append(key)
        elif any(wanted in name for name in names):
            partial.append(key)
    matches = exact or partial
    return matches[0] if len(matches) == 1 else None


def _sighting_for(session):
    if session.character is None:
        return None
    sighting = getattr(session, "_density_rare_sighting", None)
    if sighting and sighting[0] == session.character.current_room:
        return combat.ENEMIES_BY_KEY.get(sighting[1])
    return None


async def _engage(session, definition: EnemyDefinition) -> None:
    if session.active_enemy is not None:
        await session.send("You are already fighting something.\r\n")
        return
    enemy = EnemyState(definition)
    session.active_enemy = enemy
    session.active_mobile_npc_key = None
    session.combatant.next_auto_attack_at = asyncio.get_running_loop().time()
    enemy.hate.add_threat(session.character.id, 1.0)
    await session.send(f"You engage {definition.name}. Your normal weapon attacks begin automatically.\r\n")
    await session.send_client_state()
    session.combat_task = asyncio.create_task(session._combat_loop(enemy))


def _notable_trade_patch() -> None:
    if getattr(trade_experience, "_density_history_patch", False):
        return
    original = trade_experience.exchange_items

    def exchange(database, first_id, first_offer, second_id, second_offer):
        moved = original(database, first_id, first_offer, second_id, second_offer)
        if not moved:
            return False
        notable = next((key for key in (*first_offer.keys(), *second_offer.keys()) if key in ICONIC_BY_KEY or key.startswith("density_curio_")), None)
        if notable:
            with database.connect() as db:
                names = {int(row["id"]): str(row["name"]) for row in db.execute("SELECT id, name FROM characters WHERE id IN (?, ?)", (first_id, second_id)).fetchall()}
            label = crafting.ITEMS_BY_KEY.get(notable).name if notable in crafting.ITEMS_BY_KEY else notable
            _chronicle_insert(database, event_key=f"first_notable_trade:{notable}", day=ASTRALIS_CLOCK.now().day_number, category="trade", text=f"{names.get(first_id, 'Someone')} and {names.get(second_id, 'someone')} made the first recorded player trade involving {label}.")
        return True

    trade_experience.exchange_items = exchange
    trade_experience._density_history_patch = True


def install_content_density_runtime(player_session_class, world_service) -> None:
    if getattr(player_session_class, "_content_density_installed", False):
        return
    install_density_content(world_service)
    _notable_trade_patch()
    previous_move = player_session_class.move_character
    previous_finish = player_session_class._finish_enemy_defeat
    previous_prompt = player_session_class.playing_prompt

    async def move_character(self, direction: str) -> None:
        before = self.character.current_room if self.character else None
        await previous_move(self, direction)
        if self.character is None or self.character.current_room == before:
            return
        self._density_rare_sighting = None
        room = self.character.current_room
        candidates = [rare for rare in RARE_CREATURES if RARE_HOST_BY_KEY[rare.key] == room]
        if candidates and random.random() < 0.12:
            rare = random.choice(candidates)
            self._density_rare_sighting = (room, rare.key)
            await self.send("\r\nSomething unusual moved at the edge of your vision. TRACK the sign if you want to investigate; walking on loses the moment.\r\n")
        # World bosses are even rarer and are not calendar appointments.
        if room in {VEYRA_OLD_BRIDGE_KEY, GREYWAKE_WEST_MILE_KEY, SABLEWATER_DRIFTWOOD_SHRINE_KEY} and random.random() < 0.025:
            boss = WORLD_BOSSES[{VEYRA_OLD_BRIDGE_KEY: 0, GREYWAKE_WEST_MILE_KEY: 1, SABLEWATER_DRIFTWOOD_SHRINE_KEY: 2}[room]]
            self._density_rare_sighting = (room, boss.key)
            await self.send("The road has acquired a presence that was not here a moment ago. TRACK before deciding whether to approach.\r\n")

    async def finish_enemy(self, enemy) -> None:
        key = enemy.definition.key
        eligible = getattr(self, "active_enemy", None) is enemy
        await previous_finish(self, enemy)
        if not eligible or self.character is None:
            return
        day = ASTRALIS_CLOCK.now().day_number
        if key in BOSS_KEYS:
            _chronicle_insert(self.database, event_key=f"density_first_boss:{key}", day=day, character_id=self.character.id, character_name=self.character.name, category="first", text=f"{self.character.name} recorded the first defeat of {enemy.definition.name}.")
        if key in {rare.key for rare in RARE_CREATURES}:
            _chronicle_insert(self.database, event_key=f"density_first_rare:{key}", day=day, character_id=self.character.id, character_name=self.character.name, category="discovery", text=f"{self.character.name} was the first recorded traveler to bring down the rarely seen {enemy.definition.name}.")
        iconic = None
        for seed in DUNGEON_SEEDS:
            if key == f"density_{seed.key}_boss":
                iconic = seed.iconic_drop
                break
        iconic = iconic or WORLD_BOSS_ICONICS.get(key)
        if iconic and random.random() < 0.05 and iconic in crafting.ITEMS_BY_KEY:
            self.database.add_item(self.character.id, iconic, 1)
            await self.send(f"\r\nA genuinely rare object survived the fight: {crafting.ITEMS_BY_KEY[iconic].name}. Nothing in the game labels it special. Its name and usefulness will have to earn that reputation.\r\n")
            _chronicle_insert(self.database, event_key=f"density_first_item:{iconic}", day=day, character_id=self.character.id, character_name=self.character.name, category="discovery", text=f"{self.character.name} became the first recorded owner of {crafting.ITEMS_BY_KEY[iconic].name}.")

    async def playing_prompt(self) -> None:
        command = await self.prompt("\r\n> ")
        if command is None:
            self.state = type(self.state).DISCONNECTED
            return
        norm = _normalize(command)
        room = self.character.current_room if self.character else ""

        if norm.startswith("enter "):
            target = norm[6:]
            seed = next((s for s in DUNGEON_SEEDS if room == s.anchor and target in {_normalize(s.name), _normalize(s.key)}), None)
            if seed:
                self.database.set_character_room(self.character.id, DUNGEON_ROOM_KEYS[seed.key][0]); _refresh_character(self)
                await self.send(f"You enter {seed.name}. RETREAT will return you to the road if you decide this was a bad idea.\r\n")
                await self.show_current_room(); return
        if norm == "retreat":
            seed = next((s for s in DUNGEON_SEEDS if room in DUNGEON_ROOM_KEYS[s.key]), None)
            if seed and self.active_enemy is None:
                self.database.set_character_room(self.character.id, seed.anchor); _refresh_character(self)
                await self.send("You retrace the route to familiar ground.\r\n"); await self.show_current_room(); return
        for seed in DUNGEON_SEEDS:
            if room == DUNGEON_ROOM_KEYS[seed.key][3] and norm == _normalize(seed.mechanic_command):
                flag = f"density_solved_{seed.key}"
                self.database.grant_flag(self.character.id, flag)
                self.database.set_character_room(self.character.id, DUNGEON_ROOM_KEYS[seed.key][4]); _refresh_character(self)
                await self.send(seed.mechanic_text + " The way forward answers.\r\n"); await self.show_current_room(); return

        if norm == "track":
            rare = _sighting_for(self)
            if rare:
                await self.send(f"You follow the sign far enough to identify it: {rare.name}. HUNT TRACE if you want the encounter; leaving the room lets it go.\r\n")
            else:
                await self.send("You find ordinary tracks, scuffs and weather. Nothing rare is obliging you with an encounter right now.\r\n")
            return
        if norm in {"hunt trace", "follow trace"}:
            rare = _sighting_for(self)
            if rare:
                await _engage(self, rare); self._density_rare_sighting = None
            else:
                await self.send("There is no unusual trace here to follow.\r\n")
            return

        if norm == "oddjobs":
            local = [q for i, q in enumerate(ODDJOBS) if ODDJOB_STARTS[i] == room]
            if not local:
                await self.send("Nobody here currently has a small errand worth formalizing. That is normal.\r\n"); return
            await self.send("Small local errands, if you feel like being useful:\r\n")
            for q in local:
                await self.send(f"- {q.name} — TAKE ODDJOB {q.name}\r\n")
            return
        if norm.startswith("take oddjob "):
            wanted = norm[len("take oddjob "):]
            for i, q in enumerate(ODDJOBS):
                if room == ODDJOB_STARTS[i] and wanted in {_normalize(q.name), _normalize(q.key)}:
                    if self.database.get_quest(self.character.id, q.key) is None:
                        self.database.start_quest(self.character.id, q.key, "travel")
                        await self.send(f"Odd job accepted: {q.name}. {q.objective_for_step('travel')}\r\n")
                    else:
                        await self.send("You already have history with that errand.\r\n")
                    return
        if norm == "finish oddjob":
            active = []
            for i, q in enumerate(ODDJOBS):
                state = self.database.get_quest(self.character.id, q.key)
                if state and state["status"] == "active" and room == ODDJOB_DESTS[i]:
                    active.append((i, q))
            if not active:
                await self.send("None of your tiny errands ends here.\r\n"); return
            i, q = active[0]
            self.database.complete_quest(self.character.id, q.key)
            reward = CURIOS[i % len(CURIOS)]
            self.database.add_item(self.character.id, reward.key, 1)
            self.database.add_experience(self.character.id, 15)
            await self.send(f"Odd job complete: {q.name}. The ending is less heroic than expected, which is probably why it feels real. Reward: {reward.name} and 15 XP.\r\n")
            return

        if norm.startswith("show ") and room in {WAYMEET_LANTERN_MARKET_KEY, VEYRA_BRASSMARKET_KEY, SABLEWATER_EEL_DOCK_KEY}:
            key = _resolve_owned_item(self, command.strip()[5:])
            if not key:
                await self.send("You need to be carrying one unambiguous item by that name.\r\n"); return
            item = crafting.ITEMS_BY_KEY[key]
            speaker = "Nix Coil" if room == WAYMEET_LANTERN_MARKET_KEY else "a Brassmarket dealer" if room == VEYRA_BRASSMARKET_KEY else "an Eelmarket factor"
            if key in ICONIC_BY_KEY:
                source = ICONIC_BY_KEY[key].source
                await self.send(f"{speaker} turns {item.name} over carefully. 'I've heard three stories about this. One says {source}. One says that's nonsense. The third costs money.'\r\n")
            elif key.startswith("density_curio_"):
                await self.send(f"{speaker} studies {item.name}. 'Worth almost nothing. Which is not the same thing as being uninteresting.'\r\n")
            else:
                await self.send(f"{speaker} gives {item.name} a practical glance. 'Useful enough. I know somebody who'd call it ugly and somebody else who'd call that same ugliness honest.'\r\n")
            return
        if norm.startswith("ask rumor ") and room in {WAYMEET_LANTERN_MARKET_KEY, VEYRA_BRASSMARKET_KEY, SABLEWATER_EEL_DOCK_KEY}:
            subject = command.strip()[10:]
            variants = (
                f"'I heard {subject} came out of a sealed room under Veyra.'",
                f"'No. {subject} is older than Veyra. Somebody put the city story on it because cities like owning stories.'",
                f"'Both of those are wrong. Ask again after somebody actually brings one in.'",
            )
            await self.send(random.choice(variants) + "\r\n"); return

        await _delegate(self, previous_prompt, command)

    async def _delegate(self, previous, command):
        async def replay(_text=""):
            return command
        prior = self.prompt
        self.prompt = replay
        try:
            return await previous(self)
        finally:
            self.prompt = prior

    player_session_class.move_character = move_character
    player_session_class._finish_enemy_defeat = finish_enemy
    player_session_class.playing_prompt = playing_prompt
    player_session_class._content_density_installed = True
