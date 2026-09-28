"""Deep regional Blacksmithing for Astralis.

Blacksmithing is deliberately physical. Ore becomes ingots, ingots become useful
components, components become regional equipment, and quench media give each
culture its own finishing practice. Reforging is a separate workshop action that
keeps an existing item's heritage serial while changing the metal around it.
"""
from __future__ import annotations

from dataclasses import dataclass, replace

import mud.crafting as crafting
import mud.economy_loop as economy
import mud.item_heritage as heritage
import mud.profession_expansion as expansion
import mud.world as world
from mud.crafting import ItemDefinition
from mud.gear import CraftingRecipe, MaterialRequirement
from mud.room_engine import FeatureDefinition, RoomAugmentation
from mud.stats import CharacterStats, EquipmentItem
from mud.world import NpcDefinition


@dataclass(frozen=True, slots=True)
class SmithingTradition:
    key: str
    name: str
    identity: str
    smith: str
    hall: str
    quench_name: str
    quench_description: str
    quench_materials: tuple[tuple[str, int], ...]
    experiment_metal: str
    clue_name: str
    clue_text: str
    secret_name: str
    focus_a: str
    focus_b: str


TRADITIONS: tuple[SmithingTradition, ...] = (
    SmithingTradition(
        "goblin", "Goblin", "Brassgut Rivetwork", "Vrask Rivetjaw",
        "goblin_tinker_row", "Hornblack Flux",
        "Imp-horn charcoal ground into a black flux that lets mismatched pieces take a clean weld.",
        (("imp_horn", 1), ("coal", 1)), "steel", "three-color scale",
        "Three heat colors are scratched beside a crooked weld: dull red, straw, then a brief white edge. "
        "The spacing looks deliberate enough to test against ordinary Steel.",
        "Road-Eater Cleaver", "grace", "might",
    ),
    SmithingTradition(
        "dwarf", "Dwarven", "Chainmark Forge", "Brammok Chainquench",
        "dwarf_workshop_tier", "Chainmark Quench Oil",
        "A severe-smelling oil used for predictable cooling and repeatable industrial hardening.",
        (("coal", 1), ("grain_alcohol", 1)), "cobalt", "blue hammer scar",
        "A blue-gray hammer scar runs across the anvil face. The mark is too regular to be accidental "
        "and suggests that Cobalt was cooled between separate striking passes.",
        "Unbroken Freight Hammer", "hp", "might",
    ),
    SmithingTradition(
        "forest", "Forest Elf", "Greenway Edgecraft", "Ilyra Greenhammer",
        "forest_elf_hearthwalk", "Greenbark Quench",
        "Greenleaf steeped in clean water for a slow, forgiving edge quench that favors flexible work.",
        (("greenleaf", 2), ("spring_water", 1)), "iron", "leaf-shaped temper mark",
        "A leaf-shaped temper mark has been polished into the side of an old practice blade. "
        "Its color sequence suggests a deliberately soft Iron spine behind a harder edge.",
        "Root-and-Rain Sabre", "love", "grace",
    ),
    SmithingTradition(
        "moon", "Moon Elf", "Moonstep Metallurgy", "Saelith Veynstroke",
        "moon_elf_alpine_light_garden", "Moonmist Quench",
        "Cold mountain water scented with lavender so a smith can read heat by scent as well as color.",
        (("lavender_blossom", 2), ("spring_water", 1)), "moonsteel", "mirrorfold line",
        "A mirror-bright fold line is visible only when the metal catches light sideways. "
        "The repeated fold angle points toward an experiment with Moonsteel rather than a decorative polish.",
        "Night-Mirror Longblade", "mind", "grace",
    ),
    SmithingTradition(
        "human", "Human", "Cinder Guildwork", "Tavren Cindermeasure",
        "human_cinder_lane", "Cinder Brine",
        "Coal-rich brine used by Veyra smiths to produce consistent guild-standard hardness.",
        (("coal", 1), ("spring_water", 1)), "steel", "measured quench notch",
        "A row of measured notches crosses the old trough lip. Every third notch is deeper, "
        "as though an earlier smith was timing a Steel quench by counted intervals.",
        "Fifth-City Oathblade", "might", "hp",
    ),
    SmithingTradition(
        "troll", "Troll", "Frostroot Hearthsmithing", "Krukk Ashmaul",
        "troll_ember_hollow", "Hidefat Quench",
        "A practical grease-and-water quench prepared from tough hides and used to keep large tools from becoming brittle.",
        (("rough_hide", 1), ("spring_water", 1)), "emberite", "black frost scale",
        "Black scale on a retired maul has split into frost-like branches. The pattern suggests Emberite "
        "was allowed to cool slowly before the final edge was quenched.",
        "Longwinter Gatebreaker", "might", "hp",
    ),
    SmithingTradition(
        "undead", "Undead", "Sepulcher Paleiron", "Ossivar Palechisel",
        "undead_chisel_market", "Ossuary Flux",
        "Bone ash and coal mixed into a dry welding flux used for patient, low-oxygen forge work.",
        (("bone_chips", 2), ("coal", 1)), "stariron", "funerary seam",
        "A pale seam crosses a ceremonial blade without disturbing its old inscription. "
        "The seam geometry resembles the way dense Stariron moves under repeated low blows.",
        "Last Processional Sword", "mind", "hp",
    ),
    SmithingTradition(
        "spore", "Sporekin", "Lumen Bloomforge", "Morlune Sporesteel",
        "sporekin_lumen_hollow", "Glowcap Temper Paste",
        "A cool fungal paste painted onto selected surfaces so different parts of a piece shed heat at different rates.",
        (("glowcap", 2), ("spring_water", 1)), "cobalt", "spore-ring heat map",
        "Concentric rings have been daubed onto a scrap plate in old glowcap stain. "
        "The center ring is labeled with the same blue-gray tone seen in worked Cobalt.",
        "Evergrowing Wardblade", "love", "mind",
    ),
    SmithingTradition(
        "waymeet", "Crossroads", "Seven Roads Smithing", "Dessa Roadiron",
        "waymeet_hammer_thread_row", "Roadside Quench",
        "A forgiving water-and-spirit quench meant for repairs performed with whatever a caravan can actually carry.",
        (("grain_alcohol", 1), ("spring_water", 1)), "moonsteel", "seven-notch repair bar",
        "Seven repair notches cross an old practice bar. The final notch is bright and thin, "
        "as though a traveler tested Moonsteel as a repair seam rather than forging a whole new object.",
        "All-Roads Wardensword", "grace", "hp",
    ),
)
BY_KEY = {tradition.key: tradition for tradition in TRADITIONS}


def lesson_flag(region: str, metal: str) -> str:
    return f"smith_lesson_{region}_{metal}"


def secret_flag(region: str) -> str:
    return f"smith_secret_{region}"


def quench_key(region: str) -> str:
    return f"smith_quench_{region}"


def component_key(metal: str, component: str) -> str:
    return f"smith_{metal}_{component}"


def regional_piece_key(region: str, metal: str, pattern: str) -> str:
    return f"smith_{region}_{metal}_{pattern}"


PATTERNS: tuple[tuple[str, str, str, str, int], ...] = (
    ("sword", "Longsword", "weapon", "weapon_blank", 0),
    ("hammer", "Warhammer", "weapon", "weapon_blank", 3),
    ("shield", "Shield", "off_hand", "armor_plate", 5),
    ("cuirass", "Cuirass", "body", "armor_plate", 8),
    ("gauntlets", "Gauntlets", "hands", "armor_plate", 11),
    ("greaves", "Greaves", "legs", "armor_plate", 14),
)


def _focus_bonus(tradition: SmithingTradition, tier: int) -> CharacterStats:
    amount = 0 if tier < 3 else 1 if tier < 6 else 2
    values = {"might": 0, "grace": 0, "love": 0, "mind": 0, "hp": 0}
    values[tradition.focus_a] += amount
    if tier >= 5:
        values[tradition.focus_b] += 1
    return CharacterStats(**values)


def _regional_equipment(
    tradition: SmithingTradition,
    metal: crafting.MetalTierDefinition,
    slug: str,
    label: str,
    slot: str,
) -> ItemDefinition:
    tier = metal.tier
    if slug == "sword":
        stats = CharacterStats(might=tier + 1)
        armor = 0
    elif slug == "hammer":
        stats = CharacterStats(might=tier + 2, hp=tier // 3)
        armor = 0
    elif slug == "shield":
        stats = CharacterStats(hp=tier)
        armor = tier + 1
    elif slug == "cuirass":
        stats = CharacterStats(hp=tier + 1)
        armor = 2 * tier + 1
    elif slug == "gauntlets":
        stats = CharacterStats(might=1 if tier >= 3 else 0)
        armor = max(1, tier // 2)
    else:
        stats = CharacterStats(hp=max(1, tier // 2))
        armor = tier + 1
    stats = stats.plus(_focus_bonus(tradition, tier))
    name = f"{tradition.identity} {metal.name} {label}"
    return ItemDefinition(
        regional_piece_key(tradition.key, metal.key, slug),
        name,
        f"{tradition.name} smithwork in {metal.name.lower()}, finished with {tradition.quench_name}. "
        f"The piece emphasizes {tradition.identity.lower()} methods rather than a generic tier silhouette.",
        "equipment",
        EquipmentItem(name, slot, armor_class=armor, stat_bonuses=stats),
        tier=tier,
    )


def _catalog() -> tuple[tuple[ItemDefinition, ...], tuple[CraftingRecipe, ...]]:
    items: list[ItemDefinition] = [
        ItemDefinition(
            "smith_slag",
            "Forge Slag",
            "A glassy, useless lump left by an experiment that taught the smith more than it produced.",
            "material",
            tier=1,
        ),
        ItemDefinition(
            "smith_layered_steel_billet",
            "Layered Steel Billet",
            "Iron and steel forge-welded into a layered billet for tougher advanced components.",
            "material",
            tier=2,
        ),
        ItemDefinition(
            "smith_cobalt_edge_billet",
            "Cobalt-Edge Billet",
            "A steel billet carrying a narrow cobalt working edge before final shaping.",
            "material",
            tier=4,
        ),
        ItemDefinition(
            "smith_starfold_billet",
            "Starfold Billet",
            "Moonsteel repeatedly folded around dense Stariron for secret masterwork smithing.",
            "material",
            tier=7,
        ),
    ]
    recipes: list[CraftingRecipe] = [
        CraftingRecipe(
            "smith_weld_layered_steel_billet", "blacksmithing",
            "smith_layered_steel_billet", 25, 55,
            (MaterialRequirement("iron_ingot", 1), MaterialRequirement("steel_ingot", 1)),
            station_key="forge",
            description="Forge-weld iron and steel into a layered billet without letting the seam shear.",
            design_status="deep_blacksmith_alloy",
        ),
        CraftingRecipe(
            "smith_weld_cobalt_edge_billet", "blacksmithing",
            "smith_cobalt_edge_billet", 55, 90,
            (MaterialRequirement("steel_ingot", 1), MaterialRequirement("cobalt_ingot", 1)),
            station_key="forge",
            description="Weld a narrow cobalt edge onto a steel body before the final shape is established.",
            design_status="deep_blacksmith_alloy",
        ),
        CraftingRecipe(
            "smith_fold_starfold_billet", "blacksmithing",
            "smith_starfold_billet", 125, 165,
            (MaterialRequirement("moonsteel_ingot", 1), MaterialRequirement("stariron_ingot", 1)),
            station_key="forge",
            description="Fold Moonsteel around dense Stariron until both metals move as one billet.",
            design_status="deep_blacksmith_alloy",
        ),
    ]

    for metal in crafting.METAL_TIERS:
        blank = component_key(metal.key, "weapon_blank")
        plate = component_key(metal.key, "armor_plate")
        fittings = component_key(metal.key, "fittings")
        items.extend((
            ItemDefinition(
                blank, f"{metal.name} Weapon Blank",
                f"A normalized {metal.name.lower()} bar already drawn to weapon thickness, ready for regional shaping.",
                "material", tier=metal.tier,
            ),
            ItemDefinition(
                plate, f"{metal.name} Armor Plate",
                f"A hammered {metal.name.lower()} plate with enough excess edge for fitting and articulation.",
                "material", tier=metal.tier,
            ),
            ItemDefinition(
                fittings, f"{metal.name} Fittings",
                f"Matched {metal.name.lower()} rivets, bands, pins, and small fittings for finished smithwork.",
                "material", tier=metal.tier,
            ),
        ))
        recipes.extend((
            CraftingRecipe(
                f"smith_draw_{metal.key}_weapon_blank", "blacksmithing", blank,
                metal.blacksmithing_skill + 2, metal.blacksmithing_skill + 32,
                (MaterialRequirement(metal.ingot_key, 2),), station_key="forge",
                description=f"Draw two {metal.name} ingots into a normalized weapon blank before choosing the final pattern.",
                design_status="deep_blacksmith_component",
            ),
            CraftingRecipe(
                f"smith_hammer_{metal.key}_armor_plate", "blacksmithing", plate,
                metal.blacksmithing_skill + 4, metal.blacksmithing_skill + 34,
                (MaterialRequirement(metal.ingot_key, 2),), station_key="forge",
                description=f"Hammer two {metal.name} ingots into a broad armor plate with usable edge allowance.",
                design_status="deep_blacksmith_component",
            ),
            CraftingRecipe(
                f"smith_make_{metal.key}_fittings", "blacksmithing", fittings,
                metal.blacksmithing_skill + 1, metal.blacksmithing_skill + 31,
                (MaterialRequirement(metal.ingot_key, 1),), output_quantity=2,
                station_key="forge",
                description=f"Draw one {metal.name} ingot into matched pins, bands, rivets, and fittings.",
                design_status="deep_blacksmith_component",
            ),
        ))

    for tradition in TRADITIONS:
        qkey = quench_key(tradition.key)
        items.append(ItemDefinition(
            qkey, tradition.quench_name, tradition.quench_description, "material", tier=2,
        ))
        recipes.append(CraftingRecipe(
            f"smith_prepare_quench_{tradition.key}", "blacksmithing", qkey,
            5, 35,
            tuple(MaterialRequirement(key, quantity) for key, quantity in tradition.quench_materials),
            station_key="forge",
            description=f"Prepare {tradition.quench_name} for {tradition.identity} finishing work.",
            design_status="deep_blacksmith_quench",
        ))

        for metal in crafting.METAL_TIERS:
            for slug, label, slot, primary_component, offset in PATTERNS:
                item = _regional_equipment(tradition, metal, slug, label, slot)
                items.append(item)
                materials = [
                    MaterialRequirement(component_key(metal.key, primary_component), 1),
                    MaterialRequirement(component_key(metal.key, "fittings"), 1),
                    MaterialRequirement(qkey, 1),
                ]
                if slug == "cuirass":
                    materials.insert(1, MaterialRequirement(component_key(metal.key, "armor_plate"), 1))
                recipes.append(CraftingRecipe(
                    f"smith_pattern_{tradition.key}_{metal.key}_{slug}",
                    "blacksmithing",
                    item.key,
                    metal.blacksmithing_skill + 5 + offset,
                    metal.blacksmithing_skill + 40 + offset,
                    tuple(materials),
                    station_key="forge",
                    description=(
                        f"Shape and finish a {tradition.identity} {metal.name} {label.lower()} "
                        f"from standardized components, then temper it with {tradition.quench_name}."
                    ),
                    design_status="regional_blacksmith_pattern",
                    discovery_flag=lesson_flag(tradition.key, metal.key),
                ))

        secret_item_key = f"smith_secret_{tradition.key}"
        secret_name = f"{tradition.identity} {tradition.secret_name}"
        focus = _focus_bonus(tradition, 8)
        secret_stats = CharacterStats(might=10, hp=3).plus(focus)
        items.append(ItemDefinition(
            secret_item_key,
            secret_name,
            f"A secret {tradition.name.lower()} masterwork built around a Starfold seam and an Astralite body. "
            "Its technique is learned through workshop experimentation rather than ordinary training.",
            "equipment",
            EquipmentItem(secret_name, "weapon", stat_bonuses=secret_stats),
            tier=8,
        ))
        recipes.append(CraftingRecipe(
            f"smith_hidden_{tradition.key}", "blacksmithing", secret_item_key,
            185, 225,
            (
                MaterialRequirement(component_key("astralite", "weapon_blank"), 1),
                MaterialRequirement(component_key("astralite", "fittings"), 1),
                MaterialRequirement("smith_starfold_billet", 1),
                MaterialRequirement(qkey, 1),
            ),
            station_key="forge",
            description=f"Execute the hidden {tradition.identity} master technique for {tradition.secret_name}.",
            design_status="regional_blacksmith_secret",
            discovery_flag=secret_flag(tradition.key),
        ))

    return tuple(items), tuple(recipes)


ITEMS, RECIPES = _catalog()
RECIPES_BY_KEY = {recipe.key: recipe for recipe in RECIPES}


MINING_PLACEMENTS: tuple[tuple[str, str], ...] = (
    ("dwarf_upper_freight_deck", "cobalt_vein"),
    ("moon_elf_wind_terrace", "moonsilver_vein"),
    ("underclock_condenser_court", "emberite_vein"),
    ("greywake_riftfield", "stariron_deposit"),
    ("salt_kingdoms_springcut_gorge", "astralite_vein"),
)


REFORGEABLE_TOKENS = (
    "sword", "dagger", "blade", "knife", "axe", "hammer", "mace", "spear",
    "shield", "buckler", "helmet", "helm", "breastplate", "gauntlet", "greave",
)
REFORGE_VARIANTS: dict[tuple[str, str], str] = {}


def _is_reforgeable(item: ItemDefinition) -> bool:
    if item.equipment is None or item.equipment.scripted_effects:
        return False
    if item.key.startswith(("reforged_", "smith_")):
        return False
    text = f"{item.key} {item.name}".lower()
    return any(token in text for token in REFORGEABLE_TOKENS)


def _reforge_stats(item: ItemDefinition, metal: crafting.MetalTierDefinition) -> EquipmentItem:
    assert item.equipment is not None
    eq = item.equipment
    base = eq.stat_bonuses
    values = base.as_dict()
    armor = eq.armor_class
    if eq.slot == "weapon":
        values["might"] = max(values["might"], metal.tier + 1)
    elif eq.slot == "off_hand":
        armor = max(armor, metal.tier + 1)
        values["hp"] = max(values["hp"], metal.tier)
    elif eq.slot == "body":
        armor = max(armor, metal.tier * 2)
        values["hp"] = max(values["hp"], metal.tier)
    else:
        armor = max(armor, metal.tier)
        if eq.slot in {"hands", "legs"}:
            values["hp"] = max(values["hp"], max(1, metal.tier // 2))
    return replace(
        eq,
        name=f"{metal.name}-Reforged {item.name}",
        armor_class=armor,
        stat_bonuses=CharacterStats(**values),
    )


def _build_reforge_variants() -> tuple[ItemDefinition, ...]:
    additions: list[ItemDefinition] = []
    snapshot = tuple(crafting.ITEMS_BY_KEY.values())
    for base in snapshot:
        if not _is_reforgeable(base):
            continue
        for metal in crafting.METAL_TIERS:
            if metal.tier <= max(0, base.tier):
                continue
            key = f"reforged_{metal.key}_{base.key}"
            REFORGE_VARIANTS[(base.key, metal.key)] = key
            if key in crafting.ITEMS_BY_KEY:
                continue
            equipment = _reforge_stats(base, metal)
            additions.append(ItemDefinition(
                key,
                equipment.name,
                f"{base.description} Reforged in {metal.name} while keeping the original object's identity and provenance.",
                "equipment",
                equipment=equipment,
                tier=metal.tier,
            ))
    return tuple(additions)


def _original_reforge_key(item_key: str) -> str:
    for metal in crafting.METAL_TIERS:
        prefix = f"reforged_{metal.key}_"
        if item_key.startswith(prefix):
            return item_key[len(prefix):]
    return item_key


def _effective_metal_tier(item: ItemDefinition) -> int:
    for metal in crafting.METAL_TIERS:
        if item.key.startswith(f"reforged_{metal.key}_"):
            return metal.tier
    return max(0, item.tier)


def catalog_counts() -> dict[str, int]:
    return {
        "traditions": len(TRADITIONS),
        "regional_patterns": sum(r.design_status == "regional_blacksmith_pattern" for r in RECIPES),
        "components": sum(r.design_status == "deep_blacksmith_component" for r in RECIPES),
        "quench_media": sum(r.design_status == "deep_blacksmith_quench" for r in RECIPES),
        "alloy_billets": sum(r.design_status == "deep_blacksmith_alloy" for r in RECIPES),
        "hidden_techniques": sum(r.design_status == "regional_blacksmith_secret" for r in RECIPES),
        "reforge_variants": len(REFORGE_VARIANTS),
    }


def install_regional_blacksmithing_content(world_service=None) -> dict[str, int]:
    if getattr(crafting, "_regional_blacksmithing_installed", False):
        return catalog_counts()

    missing = sorted({
        room_key
        for tradition in TRADITIONS
        for room_key in (tradition.hall,)
        if room_key not in world.ROOMS_BY_KEY
    } | {
        room_key for room_key, _node_key in MINING_PLACEMENTS
        if room_key not in world.ROOMS_BY_KEY
    })
    if missing:
        raise RuntimeError(f"Regional Blacksmithing requires real rooms: {missing}")

    # Build these before regional smith gear is registered. Reforging is meant
    # for existing world, quest, drop, and ordinary crafted metal gear, not as
    # an exponential variant generator for the new regional catalog itself.
    reforge_items = _build_reforge_variants()

    expansion._register_items(ITEMS + reforge_items)
    expansion._register_recipes(RECIPES)

    for room_key, node_key in MINING_PLACEMENTS:
        if node_key not in crafting.RESOURCE_NODES_BY_KEY:
            raise RuntimeError(f"Unknown Blacksmithing resource node: {node_key}")
        current = economy.ROOM_RESOURCE_NODE_KEYS.get(room_key, ())
        if node_key not in current:
            economy.ROOM_RESOURCE_NODE_KEYS[room_key] = current + (node_key,)

    for tradition in TRADITIONS:
        npc_key = f"regional_smith_{tradition.key}"
        npc = NpcDefinition(
            npc_key,
            tradition.smith,
            f"a {tradition.name.lower()} master smith reading the color of a heated edge",
            tradition.hall,
            "regional blacksmithing teacher and forge master",
            (
                f"{tradition.smith} says: 'Bring me metal that has already been smelted. "
                "TRAIN BLACKSMITHING teaches our patterns as your hands become ready. "
                "RECIPES BLACKSMITHING shows the work you know. SMITH STUDIES explains the forge.'",
            ),
        )
        if npc_key not in world.NPCS_BY_KEY:
            world.NPCS = world.NPCS + (npc,)
        world.NPCS_BY_KEY[npc_key] = npc

        room = world.ROOMS_BY_KEY[tradition.hall]
        if npc_key not in room.npc_keys:
            updated = replace(room, npc_keys=room.npc_keys + (npc_key,))
            world.ROOMS_BY_KEY[room.key] = updated
            world.ROOMS = tuple(updated if existing.key == room.key else existing for existing in world.ROOMS)
            if world_service is not None:
                world_service.legacy_rooms[room.key] = updated

        stations = economy.ROOM_STATIONS.get(tradition.hall, ())
        if "forge" not in stations:
            economy.ROOM_STATIONS[tradition.hall] = stations + ("forge",)

        if world_service is not None:
            previous = world_service.augmentations.get(tradition.hall)
            feature = FeatureDefinition(
                key=f"smith_clue_{tradition.key}",
                name=tradition.clue_name.title(),
                summary=f"a {tradition.clue_name} preserved near the working forge",
                examine_text=(
                    tradition.clue_text
                    + " A practiced smith could try SMITH EXPERIMENT <METAL> here."
                ),
                aliases=(tradition.clue_name, "temper mark", "forge clue"),
            )
            if previous is None:
                world_service.augmentations[tradition.hall] = RoomAugmentation(features=(feature,))
            elif all(existing.key != feature.key for existing in previous.features):
                world_service.augmentations[tradition.hall] = replace(
                    previous, features=previous.features + (feature,)
                )
            cache = getattr(world_service, "_scene_cache", None)
            if cache is not None:
                cache.pop(tradition.hall, None)

    invalid = [
        (recipe.key, requirement.item_key)
        for recipe in RECIPES
        for requirement in recipe.materials
        if requirement.item_key not in crafting.ITEMS_BY_KEY
    ]
    if invalid:
        raise RuntimeError(f"Missing regional Blacksmithing materials: {invalid[:12]}")

    counts = catalog_counts()
    if counts["regional_patterns"] != 378:
        raise RuntimeError(
            f"Regional Blacksmithing must expose 378 cultural patterns, found {counts['regional_patterns']}"
        )

    crafting._regional_blacksmithing_installed = True
    return counts


def _normalize(text: str) -> str:
    return " ".join(text.casefold().strip().replace("_", " ").replace("-", " ").split())


def _local_tradition(session):
    character = getattr(session, "character", None)
    if character is None:
        return None
    return next((t for t in TRADITIONS if t.hall == character.current_room), None)


def _resolve_metal(target: str):
    wanted = _normalize(target)
    matches = []
    for metal in crafting.METAL_TIERS:
        names = {
            _normalize(metal.key),
            _normalize(metal.name),
            _normalize(metal.ingot_key),
            _normalize(f"{metal.name} ingot"),
        }
        if wanted in names:
            return metal
        if wanted and any(wanted in name for name in names):
            matches.append(metal)
    return matches[0] if len(matches) == 1 else None


async def show_crafting_studies(session) -> None:
    character = getattr(session, "character", None)
    if character is None:
        return
    known = set(session.database.list_flags(character.id))
    skill = crafting.trade_skill_value(session.database, character.id, "blacksmithing")
    local = _local_tradition(session)

    await session.send("\r\n--- BLACKSMITHING STUDIES ---\r\n")
    await session.send(
        "Ore -> ingot -> component -> regional pattern is the normal production chain. "
        "Regional quench media finish the work; layered billets and hidden techniques sit above it.\r\n"
    )
    await session.send(
        "Advanced ore sources: Cobalt in Dwarven freight workings; Moonsilver in Moon Elf highlands; "
        "Emberite in the Underclock; Stariron in Greywake; Astralite in the Salt Kingdoms.\r\n"
    )
    if local is not None:
        await session.send(
            f"Local master: {local.smith} - {local.identity}. "
            f"TRAIN BLACKSMITHING teaches the next metal family when your skill is ready.\r\n"
        )
        next_metal = next(
            (metal for metal in crafting.METAL_TIERS
             if lesson_flag(local.key, metal.key) not in known),
            None,
        )
        if next_metal is None:
            await session.send("You have learned every ordinary regional lesson from this master.\r\n")
        elif skill >= next_metal.blacksmithing_skill:
            await session.send(f"Next lesson ready: {next_metal.name}. Use TRAIN BLACKSMITHING.\r\n")
        else:
            await session.send(
                f"Next lesson: {next_metal.name} at Blacksmithing {next_metal.blacksmithing_skill}; "
                f"your skill is {skill}.\r\n"
            )
        if secret_flag(local.key) not in known:
            await session.send(
                f"Something around this forge hints at an unwritten technique. EXAMINE {local.clue_name.upper()} "
                "and experiment when you have the materials.\r\n"
            )
    else:
        await session.send("Regional forge masters:\r\n")
        for tradition in TRADITIONS:
            room = world.ROOMS_BY_KEY.get(tradition.hall)
            label = getattr(room, "name", tradition.hall.replace("_", " ").title())
            await session.send(f"  {tradition.smith} - {tradition.identity} - {label}\r\n")
    await session.send(
        "Workshop commands: TRAIN BLACKSMITHING | SMITH EXPERIMENT <metal> | "
        "REFORGE <item or serial> WITH <metal>\r\n"
    )


async def _train_blacksmithing(session) -> None:
    character = getattr(session, "character", None)
    if character is None:
        return
    tradition = _local_tradition(session)
    if tradition is None:
        await session.send(
            "Regional Blacksmithing lessons are taught at a master smith's forge. "
            "Use SMITH STUDIES to see the teaching halls.\r\n"
        )
        return
    known = set(session.database.list_flags(character.id))
    skill = crafting.trade_skill_value(session.database, character.id, "blacksmithing")
    for metal in crafting.METAL_TIERS:
        flag = lesson_flag(tradition.key, metal.key)
        if flag in known:
            continue
        if skill < metal.blacksmithing_skill:
            await session.send(
                f"{tradition.smith} says: 'Your hands are not ready for {metal.name}. "
                f"Reach Blacksmithing {metal.blacksmithing_skill}; you are at {skill}.'\r\n"
            )
            return
        session.database.grant_flag(character.id, flag)
        await session.send(
            f"{tradition.smith} teaches you the {tradition.identity} {metal.name} pattern family: "
            "longsword, warhammer, shield, cuirass, gauntlets, and greaves.\r\n"
        )
        await session.send(
            f"The patterns are now in RECIPES BLACKSMITHING. They use {metal.name} components and "
            f"{tradition.quench_name} rather than raw ingots alone.\r\n"
        )
        return
    await session.send(f"{tradition.smith} has no further ordinary lessons to teach you.\r\n")


async def _experiment(session, target: str) -> None:
    character = getattr(session, "character", None)
    if character is None:
        return
    tradition = _local_tradition(session)
    if tradition is None:
        await session.send("You need to experiment at one of the regional master forges.\r\n")
        return
    if "forge" not in set(economy._stations_here(session)):
        await session.send("You need a working forge to run a smithing experiment.\r\n")
        return
    metal = _resolve_metal(target)
    if metal is None:
        await session.send("Name one metal family, such as IRON, STEEL, COBALT, or MOONSTEEL.\r\n")
        return
    skill = crafting.trade_skill_value(session.database, character.id, "blacksmithing")
    if skill < metal.blacksmithing_skill:
        await session.send(
            f"You cannot control {metal.name} well enough to experiment with it yet. "
            f"Blacksmithing {metal.blacksmithing_skill} is required; yours is {skill}.\r\n"
        )
        return
    flag = secret_flag(tradition.key)
    known = set(session.database.list_flags(character.id))
    if flag in known:
        await session.send("You have already solved this forge's hidden technique.\r\n")
        return

    qkey = quench_key(tradition.key)
    if session.database.item_quantity(character.id, metal.ingot_key) < 1:
        await session.send(f"You need 1x {metal.name} Ingot for that experiment.\r\n")
        return
    if session.database.item_quantity(character.id, qkey) < 1:
        await session.send(f"You need 1x {tradition.quench_name} for that experiment.\r\n")
        return

    session.database.consume_item(character.id, metal.ingot_key, 1)
    session.database.consume_item(character.id, qkey, 1)

    if metal.key != tradition.experiment_metal:
        session.database.add_item(character.id, "smith_slag", 1)
        await session.send(
            f"The {metal.name} teaches you something about the heat, but the seam collapses into Forge Slag. "
            "The hidden technique remains unresolved.\r\n"
        )
        return

    session.database.grant_flag(character.id, flag)
    recipe = crafting.RECIPES_BY_KEY[f"smith_hidden_{tradition.key}"]
    await session.send(
        tradition.clue_text + "\r\n"
        f"This time the metal confirms the pattern. You discover a hidden Blacksmithing technique: "
        f"{crafting.ITEMS_BY_KEY[recipe.output_item_key].name}.\r\n"
    )
    await economy._show_recipe_detail(session, crafting.ITEMS_BY_KEY[recipe.output_item_key].name)


def _resolve_owned_reforge_target(session, target: str):
    character = getattr(session, "character", None)
    if character is None:
        return None, None, "You are not in the world."

    raw = target.strip()
    provenance = heritage.provenance_by_serial(session.database, raw)
    if provenance is not None:
        if int(provenance.get("owner_character_id") or 0) != int(character.id):
            return None, None, "That heritage serial is not yours."
        if provenance.get("holder_kind") != "character" or str(provenance.get("holder_key")) != str(character.id):
            return None, None, "That heritage item is not currently in your carried inventory."
        key = str(provenance["item_key"])
        if session.database.item_quantity(character.id, key) <= 0:
            return None, None, "That heritage record no longer matches a carried item."
        return key, str(provenance["serial"]), None

    wanted = _normalize(raw)
    matches: list[str] = []
    for row in session.database.list_items(character.id):
        key = str(row["item_key"])
        item = crafting.ITEMS_BY_KEY.get(key)
        if item is None or item.equipment is None:
            continue
        names = {_normalize(key), _normalize(item.name)}
        quality = 2 if wanted in names else 1 if wanted and any(wanted in name for name in names) else 0
        if quality == 2:
            matches = [key]
            break
        if quality == 1:
            matches.append(key)
    matches = list(dict.fromkeys(matches))
    if not matches:
        return None, None, "You are not carrying metal-compatible equipment by that name."
    if len(matches) > 1:
        labels = ", ".join(crafting.ITEMS_BY_KEY[key].name for key in matches[:6])
        return None, None, f"Be more specific: {labels}."

    key = matches[0]
    tracked = heritage.owned_heritage_rows(session.database, character.id, key, carried_only=True)
    if len(tracked) > 1:
        serials = ", ".join(str(row["serial"]) for row in tracked[:6])
        return None, None, (
            f"You carry several tracked copies of {crafting.ITEMS_BY_KEY[key].name}. "
            f"Use a heritage serial with REFORGE instead: {serials}."
        )
    serial = str(tracked[0]["serial"]) if tracked else None
    return key, serial, None


def _reforge_cost(item: ItemDefinition) -> int:
    assert item.equipment is not None
    if item.equipment.slot == "body":
        return 4
    if item.equipment.slot == "off_hand":
        return 3
    return 2


def _reforge_transaction(
    database,
    *,
    character_id: int,
    source_key: str,
    output_key: str,
    ingot_key: str,
    ingot_quantity: int,
    serial: str | None,
) -> tuple[bool, str | None, str]:
    heritage.ensure_item_heritage_schema(database)
    holder = heritage.HeritageHolder.character(character_id)
    source_name = crafting.ITEMS_BY_KEY[source_key].name
    output_name = crafting.ITEMS_BY_KEY[output_key].name

    with database.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        source_row = db.execute(
            "SELECT quantity FROM character_items WHERE character_id = ? AND item_key = ?",
            (int(character_id), source_key),
        ).fetchone()
        material_row = db.execute(
            "SELECT quantity FROM character_items WHERE character_id = ? AND item_key = ?",
            (int(character_id), ingot_key),
        ).fetchone()
        if source_row is None or int(source_row["quantity"]) < 1:
            return False, None, "The item is no longer in your inventory."
        if material_row is None or int(material_row["quantity"]) < int(ingot_quantity):
            return False, None, "The required ingots are no longer in your inventory."

        tracked = heritage._instances_at_holder_in_connection(
            db, holder=holder, item_key=source_key, owner_character_id=character_id
        )
        selected = None
        if serial is not None:
            selected = next((row for row in tracked if str(row["serial"]).casefold() == serial.casefold()), None)
            if selected is None:
                return False, None, "That heritage serial no longer matches this carried item."
        elif len(tracked) > 1:
            return False, None, "Several tracked copies exist; use a heritage serial to choose one."
        elif tracked:
            selected = tracked[0]

        if selected is None:
            character_row = db.execute(
                "SELECT name, current_room FROM characters WHERE id = ?",
                (int(character_id),),
            ).fetchone()
            maker_name = str(character_row["name"]) if character_row is not None else None
            room_key = str(character_row["current_room"] or "") if character_row is not None else ""
            seeded = heritage._insert_instance_in_connection(
                db,
                item_key=source_key,
                heritage_kind="reforge_registered",
                owner_character_id=int(character_id),
                holder=holder,
                origin_text=(
                    f"{source_name} entered the heritage registry when it was first reforged. "
                    "Any earlier unrecorded history remains unknown."
                ),
                crafted_room_key=room_key or None,
            )
            selected = db.execute(
                "SELECT * FROM item_heritage_instances WHERE id = ?",
                (int(seeded["id"]),),
            ).fetchone()
            heritage._event_in_connection(
                db,
                instance_id=int(selected["id"]),
                event_type="registered_for_reforge",
                actor_character_id=int(character_id),
                from_owner_character_id=int(character_id),
                to_owner_character_id=int(character_id),
                from_holder=holder,
                to_holder=holder,
                note=f"{source_name} entered the heritage registry before reforging.",
            )

        db.execute(
            "UPDATE character_items SET quantity = quantity - 1 WHERE character_id = ? AND item_key = ?",
            (int(character_id), source_key),
        )
        db.execute(
            "UPDATE character_items SET quantity = quantity - ? WHERE character_id = ? AND item_key = ?",
            (int(ingot_quantity), int(character_id), ingot_key),
        )
        db.execute(
            "DELETE FROM character_items WHERE character_id = ? AND quantity <= 0",
            (int(character_id),),
        )
        db.execute(
            """
            INSERT INTO character_items (character_id, item_key, quantity)
            VALUES (?, ?, 1)
            ON CONFLICT(character_id, item_key) DO UPDATE SET quantity = quantity + 1
            """,
            (int(character_id), output_key),
        )

        instance_id = int(selected["id"])
        preserved_serial = str(selected["serial"])
        db.execute(
            "UPDATE item_heritage_instances SET item_key = ? WHERE id = ?",
            (output_key, instance_id),
        )
        heritage._event_in_connection(
            db,
            instance_id=instance_id,
            event_type="reforged",
            actor_character_id=int(character_id),
            from_owner_character_id=int(character_id),
            to_owner_character_id=int(character_id),
            from_holder=holder,
            to_holder=holder,
            note=f"{source_name} was reforged into {output_name}; heritage serial {preserved_serial} was preserved.",
        )
    return True, preserved_serial, ""


async def _reforge(session, item_target: str, metal_target: str) -> None:
    character = getattr(session, "character", None)
    if character is None:
        return
    if getattr(session, "active_enemy", None) is not None:
        await session.send("You cannot reforge equipment while fighting.\r\n")
        return
    if "forge" not in set(economy._stations_here(session)):
        await session.send("REFORGE requires a working Forge. Use RESOURCES to see local stations.\r\n")
        return

    metal = _resolve_metal(metal_target)
    if metal is None:
        await session.send("Unknown target metal. Try IRON, STEEL, COBALT, MOONSTEEL, EMBERITE, STARIRON, or ASTRALITE.\r\n")
        return

    source_key, serial, error = _resolve_owned_reforge_target(session, item_target)
    if error:
        await session.send(error + "\r\n")
        return
    assert source_key is not None
    item = crafting.ITEMS_BY_KEY.get(source_key)
    if item is None or item.equipment is None:
        await session.send("That item cannot be reforged.\r\n")
        return

    original = _original_reforge_key(source_key)
    base = crafting.ITEMS_BY_KEY.get(original)
    if base is None or not _is_reforgeable(base):
        await session.send(
            "That piece is not suitable for metal reforging. Swords, blades, axes, hammers, spears, "
            "shields, helmets, breastplates, gauntlets, and greaves are the normal candidates.\r\n"
        )
        return
    current_tier = _effective_metal_tier(item)
    if metal.tier <= current_tier:
        await session.send(
            f"Reforging only moves a piece into a higher metal tier. This item is tier {current_tier}; "
            f"{metal.name} is tier {metal.tier}.\r\n"
        )
        return

    output_key = REFORGE_VARIANTS.get((original, metal.key))
    if output_key is None or output_key not in crafting.ITEMS_BY_KEY:
        await session.send("That item has no safe reforging pattern for the chosen metal.\r\n")
        return

    skill = crafting.trade_skill_value(session.database, character.id, "blacksmithing")
    required_skill = metal.blacksmithing_skill + 5
    if skill < required_skill:
        await session.send(
            f"{metal.name} reforging requires Blacksmithing {required_skill}; your skill is {skill}.\r\n"
        )
        return

    from mud.equipment_system import equipped_item_keys
    if source_key in set(equipped_item_keys(session.database, character.id).values()):
        await session.send("Unequip that item before putting it back into the forge.\r\n")
        return

    cost = _reforge_cost(item)
    if session.database.item_quantity(character.id, metal.ingot_key) < cost:
        await session.send(f"You need {cost}x {metal.name} Ingot to reforge that piece.\r\n")
        return

    source_quantity = session.database.item_quantity(character.id, source_key)
    checker = getattr(session, "can_receive_item", None)
    if source_quantity > 1 and callable(checker) and not checker(output_key, 1):
        await session.send(
            "Your inventory needs one free item-type slot because the source stack contains another copy.\r\n"
        )
        return

    ok, preserved_serial, transaction_error = _reforge_transaction(
        session.database,
        character_id=character.id,
        source_key=source_key,
        output_key=output_key,
        ingot_key=metal.ingot_key,
        ingot_quantity=cost,
        serial=serial,
    )
    if not ok:
        await session.send(transaction_error + "\r\n")
        return

    output = crafting.ITEMS_BY_KEY[output_key]
    await session.send(
        f"You reforge {item.name} into {output.name} using {cost}x {metal.name} Ingot. "
        f"The same heritage identity survives the work [{preserved_serial}].\r\n"
    )


async def _delegate(self, previous_playing_prompt, command: str) -> None:
    had = "prompt" in self.__dict__
    prior = self.__dict__.get("prompt")

    async def replay_prompt(_text: str) -> str:
        return command

    self.prompt = replay_prompt
    try:
        await previous_playing_prompt(self)
    finally:
        if had:
            self.prompt = prior
        else:
            self.__dict__.pop("prompt", None)


def _live_prompt(session) -> str:
    current = getattr(session, "current_prompt_text", None)
    if callable(current):
        try:
            return "\r\n" + str(current())
        except Exception:
            pass
    return "\r\n> "


def install_regional_blacksmithing_runtime(player_session_class) -> None:
    if getattr(player_session_class, "_regional_blacksmithing_runtime_installed", False):
        return

    install_regional_blacksmithing_content()
    previous_playing_prompt = player_session_class.playing_prompt

    async def playing_prompt(self) -> None:
        if getattr(self, "character", None) is None:
            await previous_playing_prompt(self)
            return

        command = await self.prompt(_live_prompt(self))
        if command is None:
            await previous_playing_prompt(self)
            return
        stripped = command.strip()
        normalized = _normalize(stripped)

        if normalized in {"smith studies", "blacksmithing studies", "smithing studies", "smith help", "blacksmithing help"}:
            await show_crafting_studies(self)
            return
        if normalized in {"train blacksmithing", "train smithing", "learn blacksmithing", "learn smithing"}:
            await _train_blacksmithing(self)
            return
        if normalized in {"smith experiment", "blacksmith experiment"}:
            await self.send("Use SMITH EXPERIMENT <metal> at a regional master forge.\r\n")
            return
        if normalized.startswith("smith experiment "):
            await _experiment(self, stripped.split(maxsplit=2)[2])
            return
        if normalized.startswith("blacksmith experiment "):
            await _experiment(self, stripped.split(maxsplit=2)[2])
            return
        if normalized == "reforge":
            await self.send("Use REFORGE <item or heritage serial> WITH <metal>.\r\n")
            return
        if normalized.startswith("reforge ") and " with " in normalized:
            body = stripped[len("reforge "):]
            lower = body.casefold()
            split_at = lower.rfind(" with ")
            item_target = body[:split_at].strip()
            metal_target = body[split_at + len(" with "):].strip()
            await _reforge(self, item_target, metal_target)
            return

        await _delegate(self, previous_playing_prompt, command)

    player_session_class.playing_prompt = playing_prompt
    player_session_class._regional_blacksmithing_runtime_installed = True
