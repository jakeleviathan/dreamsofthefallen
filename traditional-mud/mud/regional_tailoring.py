"""Living regional tailoring for Astralis.

Regional patterns use the same items, recipe registry, crafting transactions, skill
progression, stations, maker marks and Sols as every other profession. The only
persistent unlocks are ordinary character flags and transferable pattern folios.
"""
from __future__ import annotations

from dataclasses import dataclass, replace

import mud.crafting as crafting
import mud.economy_loop as economy
import mud.profession_expansion as expansion
import mud.world as world
from mud.crafting import ItemDefinition, ResourceNodeDefinition
from mud.gear import CraftingRecipe, MaterialRequirement
from mud.room_engine import FeatureDefinition, RoomAugmentation
from mud.stats import CharacterStats, EquipmentItem
from mud.world import NpcDefinition


@dataclass(frozen=True, slots=True)
class TailoringTradition:
    key: str
    name: str
    identity: str
    tailor: str
    hall: str
    gathering_room: str
    pigment: str
    dye: str
    lining: str
    lining_material: str
    gathering_skill: str
    gathering_minimum: int
    clue: str
    secret_name: str
    description: str


TRADITIONS: tuple[TailoringTradition, ...] = (
    TailoringTradition("goblin", "Goblin", "Brassgut Patchwork", "Tzzek Copperstitch",
        "goblin_tinker_row", "goblin_patchwork_plaza", "Coppermire Pigment",
        "Coppermire Dye", "Salvager's Lining", "rough_hide", "harvesting", 0,
        "unpicked salvage seam", "Many-Road Mantle",
        "Visible repairs, recycled hides and copper-toned stitching. No patch is wasted."),
    TailoringTradition("dwarf", "Dwarven", "Chainmark Freight", "Kharivel Ironspool",
        "dwarf_workshop_tier", "dwarf_upper_freight_deck", "Kiln-Ochre",
        "Kiln-Ochre Dye", "Freight-Reinforced Lining", "coal", "mining", 0,
        "folded freight pattern", "Unbroken Lift Coat",
        "Reinforced travel clothes, engineered seams and practical freight-work protection."),
    TailoringTradition("forest", "Forest Elf", "Greenway Living", "Orivelle Briarloom",
        "forest_elf_hearthwalk", "forest_elf_greenway", "Heartleaf Pigment",
        "Heartleaf Dye", "Rootbound Lining", "greenleaf", "harvesting", 0,
        "unfinished leaf hem", "Living Canopy Mantle",
        "Breathable natural cloth, leaf dyes and flexible seams that move with the wearer."),
    TailoringTradition("moon", "Moon Elf", "Moonstep Luminous", "Zelunth Silverfold",
        "moon_elf_alpine_light_garden", "moon_elf_wind_terrace", "Lunarglass Powder",
        "Lunarglass Dye", "Lightcatcher Lining", "lavender_blossom", "harvesting", 25,
        "mirrorfold pattern", "Nightglass Dreamcloak",
        "Pale reflective dyes, disciplined tension and exceptionally light layered garments."),
    TailoringTradition("human", "Human", "Veyra Guild", "Vetrisa Measuredhem",
        "veyra_loom_hall", "veyra_north_waterworks", "Cinder-Madder Root",
        "Cinder-Madder Dye", "Double-Sealed Lining", "iron_ore", "herbalism", 5,
        "sealed guild pattern", "Fifth-City Guildmantle",
        "Standardized cuts, double-stitched tabards and guild-certified road uniforms."),
    TailoringTradition("troll", "Troll", "Frostroot Hidebound", "Hrokkun Thawthread",
        "troll_ember_hollow", "troll_frostroot_camp", "Whitebark Pigment",
        "Whitebark Dye", "Stormproof Lining", "raw_wool", "harvesting", 10,
        "weathered survival stitch", "Longwinter Sheltercoat",
        "Wind-resistant wraps and insulating layers made to survive a long winter."),
    TailoringTradition("undead", "Undead", "Sepulcher Mourning", "Nexyra Palehemm",
        "undead_chisel_market", "undead_desert_gate", "Ashpetal Pigment",
        "Ashpetal Dye", "Memory-Keeping Lining", "bone_chips", "herbalism", 10,
        "unwritten mourning pattern", "Silent Processional Robe",
        "Funerary elegance, preservation stitching and garments carrying family history."),
    TailoringTradition("spore", "Sporekin", "Lumen Mycelial", "Phellumi Gillstitch",
        "sporekin_lumen_hollow", "sporekin_mycelial_gallery", "Glowcap Pigment",
        "Glowcap Dye", "Symbiotic Lining", "greenleaf", "herbalism", 0,
        "living sporeweave fold", "Evergrowing Memorywrap",
        "Cultivated colors, fungal pigments and adaptable seams built with living fibers."),
    TailoringTradition("waymeet", "Crossroads", "Seven Roads", "Bexlan Sevenneedle",
        "waymeet_hammer_thread_row", "waymeet_briarcut_fields", "Roadside Ochre",
        "Roadside Ochre Dye", "Caravan-Ready Lining", "raw_cotton", "harvesting", 0,
        "fifth lantern stitch", "All-Roads Wayfarer Cloak",
        "Repairable, interchangeable road gear drawing techniques from all eight homelands."),
)
BY_KEY = {tradition.key: tradition for tradition in TRADITIONS}

FOLIO_PRICES = (0, 16, 45, 105, 230, 480, 850)
PATTERNS = (
    ("vest", "Vest", "body", 2, 1, CharacterStats(hp=1), 1),
    ("cloak", "Road Cloak", "body", 3, 1, CharacterStats(grace=1), 1),
    ("gloves", "Needlewraps", "hands", 1, 1, CharacterStats(grace=1), 0),
    ("leggings", "Trail Leggings", "legs", 2, 2, CharacterStats(hp=1), 1),
    ("boots", "Soft Boots", "feet", 2, 1, CharacterStats(grace=1), 0),
    ("banner", "Trade Banner", "", 2, 1, CharacterStats(), 0),
)


def lesson_flag(region: str, tier_index: int) -> str:
    return f"tailor_lesson_{region}_{tier_index}"


def secret_flag(region: str) -> str:
    return f"tailor_secret_{region}"


def folio_key(region: str, tier_index: int) -> str:
    return f"tailor_folio_{region}_{tier_index}"


def pigment_key(region: str) -> str:
    return f"tailor_pigment_{region}"


def dye_key(region: str) -> str:
    return f"tailor_dye_{region}"


def lining_key(region: str) -> str:
    return f"tailor_lining_{region}"


def piece_key(region: str, tier: str, pattern: str) -> str:
    return f"tailor_{region}_{tier}_{pattern}"


def _gear(name: str, description: str, tier: int, slot: str, bonus: CharacterStats,
          armor: int) -> ItemDefinition:
    return ItemDefinition(
        key="", name=name, description=description, category="equipment",
        equipment=EquipmentItem(name, slot, armor_class=armor, stat_bonuses=bonus),
        tier=tier,
    )


def _catalog() -> tuple[tuple[ItemDefinition, ...], tuple[ResourceNodeDefinition, ...],
                        tuple[CraftingRecipe, ...]]:
    items: list[ItemDefinition] = []
    nodes: list[ResourceNodeDefinition] = []
    recipes: list[CraftingRecipe] = []
    for tradition in TRADITIONS:
        region = tradition.key
        pigment = pigment_key(region)
        dye = dye_key(region)
        lining = lining_key(region)
        items.extend((
            ItemDefinition(pigment, tradition.pigment,
                f"A gatherable pigment used by {tradition.name.lower()} tailors.", "material", tier=1),
            ItemDefinition(dye, tradition.dye,
                f"A durable regional textile dye: {tradition.description}", "material", tier=1),
            ItemDefinition(lining, tradition.lining,
                f"An interchangeable regional lining. {tradition.description}", "material", tier=2),
        ))
        nodes.append(ResourceNodeDefinition(
            f"tailor_pigment_node_{region}", f"{tradition.pigment} Patch",
            tradition.gathering_skill, pigment, minimum_skill=tradition.gathering_minimum,
            design_status="regional_tailoring_gathering", tier=2,
            region_hint=tradition.gathering_room.replace("_", " ").title(),
        ))
        recipes.extend((
            CraftingRecipe(f"tailor_mix_dye_{region}", "tailoring", dye, 2, 32,
                (MaterialRequirement(pigment, 2), MaterialRequirement("spring_water", 1)),
                station_key="loom", description=f"Fix {tradition.pigment} into {tradition.dye}.",
                design_status="regional_tailoring_dye"),
            CraftingRecipe(f"tailor_cut_lining_{region}", "tailoring", lining, 12, 42,
                (MaterialRequirement("cotton_cloth", 1),
                 MaterialRequirement("cotton_thread", 1),
                 MaterialRequirement(dye, 1),
                 MaterialRequirement(tradition.lining_material, 1)),
                station_key="loom", description=f"Finish {tradition.lining} with a traditional {tradition.name.lower()} reinforcing material.",
                design_status="regional_tailoring_lining"),
        ))
        for ti, textile in enumerate(crafting.TEXTILE_TIERS):
            if ti > 0:
                items.append(ItemDefinition(
                    folio_key(region, ti),
                    f"{tradition.identity} {textile.name} Pattern Folio",
                    f"A transferable book of {tradition.name.lower()} {textile.name.lower()} tailoring patterns. READ it to learn this collection.",
                    "book", tier=textile.tier,
                ))
            for offset, (slug, label, slot, cloth, thread, bonus, needs_lining) in enumerate(PATTERNS):
                output = piece_key(region, textile.key, slug)
                name = f"{tradition.identity} {textile.name} {label}"
                materials = [
                    MaterialRequirement(textile.cloth_item_key, cloth),
                    MaterialRequirement(textile.thread_item_key, thread),
                    MaterialRequirement(dye, 1),
                ]
                if needs_lining:
                    materials.append(MaterialRequirement(lining, 1))
                if slot:
                    # Defensive vs magical differences stay modest and class-neutral.
                    if slot == "body":
                        stats = CharacterStats(
                            grace=(ti // 3 if slug == "cloak" else 0) + bonus.grace,
                            mind=(ti // 3 if slug == "vest" else 0),
                            hp=ti // 2 + bonus.hp,
                            love=1 if region in {"forest", "undead", "spore"} and ti >= 3 else 0,
                        )
                    elif slot == "legs":
                        stats = CharacterStats(hp=ti // 2 + 1, grace=ti // 4)
                    else:
                        stats = CharacterStats(grace=bonus.grace + ti // 4,
                            love=1 if region in {"moon", "spore"} and ti >= 4 else 0)
                    armor = max(0, ti // 3) + (1 if slot in {"body", "legs"} else 0)
                    item = _gear(name, tradition.description, textile.tier, slot, stats, armor)
                    items.append(replace(item, key=output))
                else:
                    items.append(ItemDefinition(output, name,
                        f"A saleable {tradition.name.lower()} trade banner with unmistakable regional stitching.",
                        "material", tier=textile.tier))
                recipes.append(CraftingRecipe(
                    f"tailor_pattern_{region}_{textile.key}_{slug}", "tailoring",
                    output, textile.tailoring_skill + 3 + offset * 2,
                    textile.tailoring_skill + 33 + offset * 2, tuple(materials),
                    station_key="loom",
                    description=f"Use {tradition.identity} cuts and {tradition.dye} to sew a {textile.name.lower()} {label.lower()}.",
                    design_status="regional_tailoring_pattern",
                    discovery_flag=lesson_flag(region, ti),
                ))
        master = piece_key(region, "astralweave", "secret")
        name = f"{tradition.identity} {tradition.secret_name}"
        item = _gear(name,
            f"An exceptionally intricate regional masterwork; {tradition.description}",
            8, "body",
            CharacterStats(grace=3, mind=3 if region in {"moon", "human"} else 1,
                           love=3 if region in {"forest", "spore", "undead"} else 1, hp=4),
            4,
        )
        items.append(replace(item, key=master))
        recipes.append(CraftingRecipe(
            f"tailor_hidden_{region}", "tailoring", master, 185, 225,
            (MaterialRequirement("astralweave_cloth", 4),
             MaterialRequirement("astral_thread", 3),
             MaterialRequirement("ghost_thread", 2),
             MaterialRequirement(lining, 1), MaterialRequirement(dye, 2)),
            station_key="loom",
            description=f"A secret {tradition.name.lower()} master pattern for {tradition.secret_name}.",
            design_status="regional_tailoring_secret",
            discovery_flag=secret_flag(region),
        ))
    return tuple(items), tuple(nodes), tuple(recipes)


ITEMS, NODES, RECIPES = _catalog()
RECIPES_BY_KEY = {recipe.key: recipe for recipe in RECIPES}


def install_regional_tailoring_content(world_service=None) -> dict[str, int]:
    """Register once after every regional installer has populated real rooms."""
    if getattr(crafting, "_regional_tailoring_installed", False):
        return catalog_counts()
    missing = sorted({r for t in TRADITIONS for r in (t.hall, t.gathering_room)
                      if r not in world.ROOMS_BY_KEY})
    if missing:
        raise RuntimeError(f"Regional Tailoring requires real rooms: {missing}")

    expansion._register_items(ITEMS)
    expansion._register_nodes(NODES)
    expansion._register_recipes(RECIPES)
    for tradition in TRADITIONS:
        npc_key = f"regional_tailor_{tradition.key}"
        npc = NpcDefinition(npc_key, tradition.tailor,
            f"a {tradition.name.lower()} master tailor carefully examining a half-finished garment",
            tradition.hall, "regional tailoring teacher and commission giver",
            (f"{tradition.tailor} says: '{tradition.description} RECIPES TAILORING shows "
             "the patterns I can teach you. TRAIN TAILORING for an apprentice lesson, "
             "BROWSE PATTERNS for folios and COMMISSION for today's work.'",))
        if npc_key not in world.NPCS_BY_KEY:
            world.NPCS = world.NPCS + (npc,)
        world.NPCS_BY_KEY[npc_key] = npc
        room = world.ROOMS_BY_KEY[tradition.hall]
        if npc_key not in room.npc_keys:
            updated = replace(room, npc_keys=room.npc_keys + (npc_key,))
            world.ROOMS_BY_KEY[room.key] = updated
            world.ROOMS = tuple(updated if existing.key == room.key else existing
                                for existing in world.ROOMS)
            if world_service is not None:
                world_service.legacy_rooms[room.key] = updated
        existing_stations = economy.ROOM_STATIONS.get(tradition.hall, ())
        economy.ROOM_STATIONS[tradition.hall] = existing_stations + tuple(
            key for key in ("loom",) if key not in existing_stations)
        existing_nodes = economy.ROOM_RESOURCE_NODE_KEYS.get(tradition.gathering_room, ())
        node_key = f"tailor_pigment_node_{tradition.key}"
        if node_key not in existing_nodes:
            economy.ROOM_RESOURCE_NODE_KEYS[tradition.gathering_room] = existing_nodes + (node_key,)
        if world_service is not None:
            previous = world_service.augmentations.get(tradition.hall)
            feature = FeatureDefinition(
                key=f"tailor_clue_{tradition.key}",
                name=tradition.clue.title(),
                summary=f"a {tradition.clue} half-hidden among the tailor's working notes",
                examine_text=(f"Fine tension marks are hidden in the {tradition.clue}. "
                    f"You suspect a forgotten pattern. STUDY {tradition.clue.upper()} to trace it."),
                aliases=(tradition.clue,),
            )
            if previous is None:
                world_service.augmentations[tradition.hall] = RoomAugmentation(features=(feature,))
            elif all(existing.key != feature.key for existing in previous.features):
                world_service.augmentations[tradition.hall] = replace(
                    previous, features=previous.features + (feature,))
            cache = getattr(world_service, "_scene_cache", None)
            if cache is not None:
                cache.pop(tradition.hall, None)

    # Tiered fibers are placed at established locations rather than existing
    # only as unused resource definitions. These supplement any current nodes.
    textile_sources = (
        ("troll_frostroot_camp", "wool_flock"),
        ("forest_elf_outer_grove", "silk_cocoon_cluster"),
        ("moon_elf_wind_terrace", "moonflax_bed"),
        ("greywake_riftfield", "giant_spider_nest"),
        ("gravewatch_chapel_nave", "ghostmoss_patch"),
        ("salt_kingdoms_springcut_gorge", "astral_bloom"),
    )
    for room_key, node_key in textile_sources:
        if room_key not in world.ROOMS_BY_KEY:
            raise RuntimeError(f"Tailoring fiber source needs real room: {room_key}")
        if node_key not in crafting.RESOURCE_NODES_BY_KEY:
            raise RuntimeError(f"Unknown Tailoring fiber resource: {node_key}")
        old = economy.ROOM_RESOURCE_NODE_KEYS.get(room_key, ())
        if node_key not in old:
            economy.ROOM_RESOURCE_NODE_KEYS[room_key] = old + (node_key,)

    invalid = [(r.key, m.item_key) for r in RECIPES for m in r.materials
               if m.item_key not in crafting.ITEMS_BY_KEY]
    if invalid:
        raise RuntimeError(f"Missing regional Tailoring materials: {invalid[:10]}")
    crafting._regional_tailoring_installed = True
    return catalog_counts()


def catalog_counts() -> dict[str, int]:
    return {
        "traditions": len(TRADITIONS),
        "regional_patterns": sum(r.design_status == "regional_tailoring_pattern" for r in RECIPES),
        "regional_dyes_and_linings": sum(r.design_status in {
            "regional_tailoring_dye", "regional_tailoring_lining"} for r in RECIPES),
        "hidden_patterns": sum(r.design_status == "regional_tailoring_secret" for r in RECIPES),
        "pattern_folios": sum(item.category == "book" for item in ITEMS),
    }
