from __future__ import annotations

from dataclasses import dataclass
import random
from typing import TYPE_CHECKING

from mud.gear import CraftingRecipe, MaterialRequirement
from mud.stats import CharacterStats, EquipmentItem

if TYPE_CHECKING:
    from mud.database import Database


@dataclass(frozen=True, slots=True)
class ProfessionDefinition:
    key: str
    name: str
    description: str
    primary_outputs: tuple[str, ...]


# The authored profession roster agreed on so far. These are crafting trades;
# Mining is a gathering skill and is intentionally modeled separately below.
PROFESSIONS: tuple[ProfessionDefinition, ...] = (
    ProfessionDefinition(
        key="blacksmithing",
        name="Blacksmithing",
        description="Forges metal weapons and armor from processed ore.",
        primary_outputs=("metal weapons", "metal armor"),
    ),
    ProfessionDefinition(
        key="tailoring",
        name="Tailoring",
        description="Produces cloth equipment and other sewn goods.",
        primary_outputs=("cloth equipment",),
    ),
    ProfessionDefinition(
        key="enchanting",
        name="Enchanting",
        description="Creates or enhances magical equipment and effects.",
        primary_outputs=("magical items", "enchanted equipment"),
    ),
    ProfessionDefinition(
        key="alchemy",
        name="Alchemy",
        description="Brews potions, tinctures, antidotes, essential oils, perfumes, and other alchemical goods.",
        primary_outputs=("potions", "elixirs", "tinctures", "antidotes", "essential oils", "perfumes"),
    ),
    ProfessionDefinition(
        key="cooking",
        name="Cooking",
        description="Prepares food, including consumables that may provide temporary benefits.",
        primary_outputs=("food", "temporary-buff food"),
    ),
)
PROFESSIONS_BY_KEY = {profession.key: profession for profession in PROFESSIONS}


@dataclass(frozen=True, slots=True)
class GatheringSkillDefinition:
    key: str
    name: str
    description: str
    node_based: bool = True


GATHERING_SKILLS: tuple[GatheringSkillDefinition, ...] = (
    GatheringSkillDefinition(
        key="mining",
        name="Mining",
        description="Extracts ore and fuel from authored resource nodes in the world.",
        node_based=True,
    ),
    GatheringSkillDefinition(
        key="harvesting",
        name="Harvesting",
        description="Gathers useful plant fibers and other cultivated natural materials from authored resource nodes.",
        node_based=True,
    ),
    GatheringSkillDefinition(
        key="herbalism",
        name="Herbalism",
        description="Gathers medicinal and aromatic herbs from authored herb nodes for Alchemy.",
        node_based=True,
    ),
)
GATHERING_SKILLS_BY_KEY = {skill.key: skill for skill in GATHERING_SKILLS}


@dataclass(frozen=True, slots=True)
class MetalTierDefinition:
    """Authored Blacksmithing metal progression for Astralis.

    Skill numbers are centralized development tuning. The identity and ordering
    of the metals are the important design decisions; balance can move later.
    """

    key: str
    name: str
    tier: int
    blacksmithing_skill: int
    mining_skill: int | None
    raw_material_key: str | None
    ingot_key: str
    description: str
    region_hint: str
    alloy_note: str = ""


METAL_TIERS: tuple[MetalTierDefinition, ...] = (
    MetalTierDefinition(
        key="iron",
        name="Iron",
        tier=1,
        blacksmithing_skill=0,
        mining_skill=0,
        raw_material_key="iron_ore",
        ingot_key="iron_ingot",
        description="The common beginner metal of Astralis: dependable, cheap, and widely worked.",
        region_hint="Common veins across settled regions.",
    ),
    MetalTierDefinition(
        key="steel",
        name="Steel",
        tier=2,
        blacksmithing_skill=15,
        mining_skill=None,
        raw_material_key=None,
        ingot_key="steel_ingot",
        description="Refined iron hardened with coal; the first meaningful step beyond beginner ironwork.",
        region_hint="Forged anywhere with a proper forge; its coal is especially common around industrial regions.",
        alloy_note="Made from Iron Ingots and Coal rather than mined as an ore.",
    ),
    MetalTierDefinition(
        key="cobalt",
        name="Cobalt",
        tier=3,
        blacksmithing_skill=30,
        mining_skill=25,
        raw_material_key="cobalt_ore",
        ingot_key="cobalt_ingot",
        description="A tougher blue-gray metal found in deeper deposits and favored for more accomplished work.",
        region_hint="Deeper mines, mountain workings, and dangerous old excavations.",
    ),
    MetalTierDefinition(
        key="moonsteel",
        name="Moonsteel",
        tier=4,
        blacksmithing_skill=50,
        mining_skill=45,
        raw_material_key="moonsilver_ore",
        ingot_key="moonsteel_ingot",
        description="An elegant Astralian alloy made by folding rare Moonsilver into high-quality steel.",
        region_hint="Moonsilver occurs most often in high-altitude stone beneath moonlit ranges.",
        alloy_note="Made from Steel Ingots and Moonsilver Ore.",
    ),
    MetalTierDefinition(
        key="emberite",
        name="Emberite",
        tier=5,
        blacksmithing_skill=75,
        mining_skill=70,
        raw_material_key="emberite_ore",
        ingot_key="emberite_ingot",
        description="A dark, heat-loving metal whose ore is warm even before it reaches the forge.",
        region_hint="Volcanic zones, geothermal caverns, and deep fault systems.",
    ),
    MetalTierDefinition(
        key="stariron",
        name="Stariron",
        tier=6,
        blacksmithing_skill=105,
        mining_skill=100,
        raw_material_key="stariron_ore",
        ingot_key="stariron_ingot",
        description="Dense meteoric metal recovered from ancient impact sites and buried starfall deposits.",
        region_hint="Remote craters, exposed impact strata, and dangerous ancient starfall sites.",
    ),
    MetalTierDefinition(
        key="astralite",
        name="Astralite",
        tier=7,
        blacksmithing_skill=140,
        mining_skill=135,
        raw_material_key="astralite_ore",
        ingot_key="astralite_ingot",
        description="The rare signature endgame metal of Astralis, exceptionally difficult to mine and work.",
        region_hint="Endgame-depth veins and exceptional deposits in the most dangerous regions of Astralis.",
    ),
)
METAL_TIERS_BY_KEY = {tier.key: tier for tier in METAL_TIERS}


@dataclass(frozen=True, slots=True)
class TextileTierDefinition:
    """Authored Tailoring textile progression for Astralis.

    Early tiers use familiar fibers; later tiers become increasingly specific to
    Astralis. Skill values are provisional tuning, while the ordering and
    material identities are the authored progression.
    """

    key: str
    name: str
    tier: int
    tailoring_skill: int
    harvesting_skill: int
    raw_material_key: str
    thread_item_key: str
    cloth_item_key: str
    raw_material_name: str
    thread_item_name: str
    cloth_item_name: str
    description: str
    region_hint: str


TEXTILE_TIERS: tuple[TextileTierDefinition, ...] = (
    TextileTierDefinition(
        key="cotton",
        name="Cotton",
        tier=1,
        tailoring_skill=0,
        harvesting_skill=0,
        raw_material_key="raw_cotton",
        thread_item_key="cotton_thread",
        cloth_item_key="cotton_cloth",
        raw_material_name="Raw Cotton",
        thread_item_name="Cotton Thread",
        cloth_item_name="Cotton Cloth",
        description="The common beginner textile of Astralis: inexpensive, comfortable, and easy to work.",
        region_hint="Cultivated fields and warm lowland settlements.",
    ),
    TextileTierDefinition(
        key="wool",
        name="Wool",
        tier=2,
        tailoring_skill=15,
        harvesting_skill=10,
        raw_material_key="raw_wool",
        thread_item_key="wool_yarn",
        cloth_item_key="wool_cloth",
        raw_material_name="Raw Wool",
        thread_item_name="Wool Yarn",
        cloth_item_name="Wool Cloth",
        description="Warm, durable cloth that marks the first step beyond beginner cotton work.",
        region_hint="Pastoral settlements, upland farms, and cool grasslands.",
    ),
    TextileTierDefinition(
        key="silk",
        name="Silk",
        tier=3,
        tailoring_skill=30,
        harvesting_skill=25,
        raw_material_key="silk_cocoons",
        thread_item_key="silk_thread",
        cloth_item_key="silk_cloth",
        raw_material_name="Silk Cocoons",
        thread_item_name="Silk Thread",
        cloth_item_name="Silk Cloth",
        description="Fine natural fiber requiring more skill to harvest, unwind, and sew cleanly.",
        region_hint="Warm groves, cultivated silkworm houses, and sheltered forest settlements.",
    ),
    TextileTierDefinition(
        key="moonweave",
        name="Moonweave",
        tier=4,
        tailoring_skill=50,
        harvesting_skill=45,
        raw_material_key="moonflax_fiber",
        thread_item_key="moon_thread",
        cloth_item_key="moonweave_cloth",
        raw_material_name="Moonflax Fiber",
        thread_item_name="Moon Thread",
        cloth_item_name="Moonweave Cloth",
        description="Pale cloth woven from high-altitude Moonflax, prized for its lightness and elegant sheen.",
        region_hint="High mountain terraces and moonlit slopes associated with Moon Elf lands.",
    ),
    TextileTierDefinition(
        key="spidersilk",
        name="Spidersilk",
        tier=5,
        tailoring_skill=75,
        harvesting_skill=70,
        raw_material_key="raw_spidersilk",
        thread_item_key="spidersilk_thread",
        cloth_item_key="spidersilk_cloth",
        raw_material_name="Raw Spidersilk",
        thread_item_name="Spidersilk Thread",
        cloth_item_name="Spidersilk Cloth",
        description="Exceptionally strong natural fiber gathered from dangerous giant-spider nests and carefully cleaned for weaving.",
        region_hint="Deep forests, caves, ruined places, and other regions claimed by giant spiders.",
    ),
    TextileTierDefinition(
        key="ghostweave",
        name="Ghostweave",
        tier=6,
        tailoring_skill=105,
        harvesting_skill=100,
        raw_material_key="ghostmoss_fiber",
        thread_item_key="ghost_thread",
        cloth_item_key="ghostweave_cloth",
        raw_material_name="Ghostmoss Fiber",
        thread_item_name="Ghost Thread",
        cloth_item_name="Ghostweave Cloth",
        description="A pale funerary textile made from fibrous Ghostmoss that thrives in ancient, death-soaked places.",
        region_hint="Necropolises, catacombs, ruined kingdoms, and other old places of death.",
    ),
    TextileTierDefinition(
        key="astralweave",
        name="Astralweave",
        tier=7,
        tailoring_skill=140,
        harvesting_skill=135,
        raw_material_key="astral_bloom_fiber",
        thread_item_key="astral_thread",
        cloth_item_key="astralweave_cloth",
        raw_material_name="Astral Bloom Fiber",
        thread_item_name="Astral Thread",
        cloth_item_name="Astralweave Cloth",
        description="The signature masterwork textile of Astralis, woven from exceptionally rare fibers found only in dangerous endgame regions.",
        region_hint="Rare Astral Bloom growths in remote, high-danger endgame regions.",
    ),
)
TEXTILE_TIERS_BY_KEY = {tier.key: tier for tier in TEXTILE_TIERS}


@dataclass(frozen=True, slots=True)
class ResourceNodeDefinition:
    key: str
    name: str
    gathering_skill_key: str | None
    output_item_key: str
    minimum_skill: int = 0
    node_based: bool = True
    design_status: str = "locked_identity_tuning_pending"
    tier: int = 1
    region_hint: str = ""


@dataclass(slots=True)
class ResourceNodeState:
    """Runtime state for a world resource node.

    Room/world persistence is not built yet, so depletion state currently lives
    with the node instance. The room system can later own and respawn these
    states without changing the gathering API.
    """

    definition: ResourceNodeDefinition
    remaining_uses: int

    @property
    def depleted(self) -> bool:
        return self.remaining_uses <= 0

    def gather(self, *, skill_value: int) -> str | None:
        if self.depleted or skill_value < self.definition.minimum_skill:
            return None
        self.remaining_uses -= 1
        return self.definition.output_item_key


IRON_VEIN = ResourceNodeDefinition(
    key="iron_vein",
    name="Iron Vein",
    gathering_skill_key="mining",
    output_item_key="iron_ore",
    minimum_skill=0,
    design_status="locked_low_level_resource",
    tier=1,
    region_hint="Common veins across settled regions.",
)
COTTON_PATCH = ResourceNodeDefinition(
    key="cotton_patch",
    name="Cotton Patch",
    gathering_skill_key="harvesting",
    output_item_key="raw_cotton",
    minimum_skill=0,
    design_status="locked_low_level_tailoring_resource",
    tier=1,
    region_hint="Cultivated fields and warm lowland settlements where cotton can be grown.",
)
WOOL_FLOCK = ResourceNodeDefinition(
    key="wool_flock",
    name="Sheep Flock",
    gathering_skill_key="harvesting",
    output_item_key="raw_wool",
    minimum_skill=10,
    design_status="locked_tailoring_progression_resource",
    tier=2,
    region_hint=TEXTILE_TIERS_BY_KEY["wool"].region_hint,
)
SILK_COCOON_CLUSTER = ResourceNodeDefinition(
    key="silk_cocoon_cluster",
    name="Silk Cocoon Cluster",
    gathering_skill_key="harvesting",
    output_item_key="silk_cocoons",
    minimum_skill=25,
    design_status="locked_tailoring_progression_resource",
    tier=3,
    region_hint=TEXTILE_TIERS_BY_KEY["silk"].region_hint,
)
MOONFLAX_BED = ResourceNodeDefinition(
    key="moonflax_bed",
    name="Moonflax Bed",
    gathering_skill_key="harvesting",
    output_item_key="moonflax_fiber",
    minimum_skill=45,
    design_status="locked_tailoring_progression_resource",
    tier=4,
    region_hint=TEXTILE_TIERS_BY_KEY["moonweave"].region_hint,
)
GIANT_SPIDER_NEST = ResourceNodeDefinition(
    key="giant_spider_nest",
    name="Giant Spider Nest",
    gathering_skill_key="harvesting",
    output_item_key="raw_spidersilk",
    minimum_skill=70,
    design_status="locked_tailoring_progression_resource",
    tier=5,
    region_hint=TEXTILE_TIERS_BY_KEY["spidersilk"].region_hint,
)
GHOSTMOSS_PATCH = ResourceNodeDefinition(
    key="ghostmoss_patch",
    name="Ghostmoss Patch",
    gathering_skill_key="harvesting",
    output_item_key="ghostmoss_fiber",
    minimum_skill=100,
    design_status="locked_tailoring_progression_resource",
    tier=6,
    region_hint=TEXTILE_TIERS_BY_KEY["ghostweave"].region_hint,
)
ASTRAL_BLOOM = ResourceNodeDefinition(
    key="astral_bloom",
    name="Astral Bloom",
    gathering_skill_key="harvesting",
    output_item_key="astral_bloom_fiber",
    minimum_skill=135,
    design_status="locked_tailoring_progression_resource",
    tier=7,
    region_hint=TEXTILE_TIERS_BY_KEY["astralweave"].region_hint,
)
GREENLEAF_PATCH = ResourceNodeDefinition(
    key="greenleaf_patch",
    name="Greenleaf Patch",
    gathering_skill_key="herbalism",
    output_item_key="greenleaf",
    minimum_skill=0,
    design_status="locked_low_level_alchemy_resource",
    tier=1,
    region_hint="Common meadows, forest edges, gardens, and other settled low-level regions.",
)
BITTERROOT_CLUSTER = ResourceNodeDefinition(
    key="bitterroot_cluster",
    name="Bitterroot Cluster",
    gathering_skill_key="herbalism",
    output_item_key="bitterroot",
    minimum_skill=5,
    design_status="locked_low_level_alchemy_resource",
    tier=1,
    region_hint="Damp soil, shaded woodland edges, and medicinal herb gardens.",
)
LAVENDER_PATCH = ResourceNodeDefinition(
    key="lavender_patch",
    name="Lavender Patch",
    gathering_skill_key="herbalism",
    output_item_key="lavender_blossom",
    minimum_skill=10,
    design_status="locked_early_alchemy_resource",
    tier=1,
    region_hint="Sunny fields, cultivated gardens, and dry hillsides near settlements.",
)
FRESH_WATER_SOURCE = ResourceNodeDefinition(
    key="fresh_water_source",
    name="Fresh Water Source",
    gathering_skill_key=None,
    output_item_key="spring_water",
    minimum_skill=0,
    design_status="renewable_world_fresh_water",
    tier=1,
    region_hint="Protected wells, clear streams, cisterns, rain catchments, and other explicitly clean freshwater sources.",
)
COAL_SEAM = ResourceNodeDefinition(
    key="coal_seam",
    name="Coal Seam",
    gathering_skill_key="mining",
    output_item_key="coal",
    minimum_skill=5,
    design_status="locked_steel_fuel_resource",
    tier=1,
    region_hint="Hills, mountain mines, and especially dwarven industrial workings.",
)
COBALT_VEIN = ResourceNodeDefinition(
    key="cobalt_vein",
    name="Cobalt Vein",
    gathering_skill_key="mining",
    output_item_key="cobalt_ore",
    minimum_skill=25,
    tier=3,
    region_hint=METAL_TIERS_BY_KEY["cobalt"].region_hint,
)
MOONSILVER_VEIN = ResourceNodeDefinition(
    key="moonsilver_vein",
    name="Moonsilver Vein",
    gathering_skill_key="mining",
    output_item_key="moonsilver_ore",
    minimum_skill=45,
    tier=4,
    region_hint=METAL_TIERS_BY_KEY["moonsteel"].region_hint,
)
EMBERITE_VEIN = ResourceNodeDefinition(
    key="emberite_vein",
    name="Emberite Vein",
    gathering_skill_key="mining",
    output_item_key="emberite_ore",
    minimum_skill=70,
    tier=5,
    region_hint=METAL_TIERS_BY_KEY["emberite"].region_hint,
)
STARIRON_DEPOSIT = ResourceNodeDefinition(
    key="stariron_deposit",
    name="Stariron Deposit",
    gathering_skill_key="mining",
    output_item_key="stariron_ore",
    minimum_skill=100,
    tier=6,
    region_hint=METAL_TIERS_BY_KEY["stariron"].region_hint,
)
ASTRALITE_VEIN = ResourceNodeDefinition(
    key="astralite_vein",
    name="Astralite Vein",
    gathering_skill_key="mining",
    output_item_key="astralite_ore",
    minimum_skill=135,
    tier=7,
    region_hint=METAL_TIERS_BY_KEY["astralite"].region_hint,
)

RESOURCE_NODES = (
    IRON_VEIN,
    COTTON_PATCH,
    WOOL_FLOCK,
    SILK_COCOON_CLUSTER,
    MOONFLAX_BED,
    GIANT_SPIDER_NEST,
    GHOSTMOSS_PATCH,
    ASTRAL_BLOOM,
    GREENLEAF_PATCH,
    BITTERROOT_CLUSTER,
    LAVENDER_PATCH,
    FRESH_WATER_SOURCE,
    COAL_SEAM,
    COBALT_VEIN,
    MOONSILVER_VEIN,
    EMBERITE_VEIN,
    STARIRON_DEPOSIT,
    ASTRALITE_VEIN,
)
RESOURCE_NODES_BY_KEY = {node.key: node for node in RESOURCE_NODES}


@dataclass(frozen=True, slots=True)
class ConsumableEffect:
    """Authored effect metadata for potions, tinctures, perfumes, and similar items.

    The combat/status-effect runtime will later consume this data. Keeping it on
    the item now makes crafted Alchemy outputs mechanically meaningful without
    prematurely inventing a complete buff/debuff engine.
    """

    use_mode: str = "drink"
    heal_hp: int = 0
    temporary_stat_bonuses: CharacterStats = CharacterStats()
    duration_ticks: int = 0
    effect_tags: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ItemDefinition:
    key: str
    name: str
    description: str
    category: str
    equipment: EquipmentItem | None = None
    consumable: ConsumableEffect | None = None
    tier: int = 0


def _equipment_items_for_tier(
    *,
    metal_key: str,
    metal_name: str,
    tier: int,
) -> tuple[ItemDefinition, ...]:
    """Create the four baseline equipment patterns shared across metal tiers.

    Exact stats are provisional. Keeping the same silhouettes across tiers makes
    the progression easy to read while future named drops and rare effects can
    break the pattern deliberately.
    """

    return (
        ItemDefinition(
            f"{metal_key}_dagger",
            f"{metal_name} Dagger",
            f"A tier {tier} {metal_name.lower()} dagger.",
            "equipment",
            EquipmentItem(
                f"{metal_name} Dagger",
                "weapon",
                stat_bonuses=CharacterStats(might=tier),
            ),
            tier=tier,
        ),
        ItemDefinition(
            f"{metal_key}_sword",
            f"{metal_name} Sword",
            f"A tier {tier} {metal_name.lower()} sword.",
            "equipment",
            EquipmentItem(
                f"{metal_name} Sword",
                "weapon",
                stat_bonuses=CharacterStats(might=tier + 1),
            ),
            tier=tier,
        ),
        ItemDefinition(
            f"{metal_key}_helmet",
            f"{metal_name} Helmet",
            f"A tier {tier} {metal_name.lower()} helmet.",
            "equipment",
            EquipmentItem(f"{metal_name} Helmet", "head", armor_class=tier),
            tier=tier,
        ),
        ItemDefinition(
            f"{metal_key}_breastplate",
            f"{metal_name} Breastplate",
            f"A tier {tier} {metal_name.lower()} breastplate.",
            "equipment",
            EquipmentItem(
                f"{metal_name} Breastplate",
                "body",
                armor_class=2 * tier + 1,
                stat_bonuses=CharacterStats(hp=tier),
            ),
            tier=tier,
        ),
    )


_MATERIAL_ITEMS: tuple[ItemDefinition, ...] = (
    ItemDefinition(
        "starter_weapon",
        "Basic Starting Weapon",
        "A plain but serviceable weapon issued to every new adventurer.",
        "equipment",
        equipment=EquipmentItem("Basic Starting Weapon", "weapon"),
        tier=0,
    ),
    ItemDefinition(
        "brute_training_harness",
        "Brute Training Harness",
        "Heavy beginner armor issued to Brutes; together it establishes their starting AC of 8.",
        "equipment",
        equipment=EquipmentItem(
            "Brute Training Harness",
            "body",
            armor_class=8,
            allowed_classes=frozenset({"brute"}),
        ),
        tier=0,
    ),
    ItemDefinition(
        "sealed_cathedral_note",
        "Sealed Cathedral Note",
        "A folded note closed with dark wax. It directs a newly arrived Human to present themselves to the High Acolyte in the city cathedral.",
        "quest_item",
        tier=0,
    ),
    ItemDefinition("raw_cotton", "Raw Cotton", "Soft plant fiber gathered from cotton patches.", "material", tier=1),
    ItemDefinition("cotton_thread", "Cotton Thread", "Spun cotton thread ready for weaving and sewing.", "material", tier=1),
    ItemDefinition("cotton_cloth", "Cotton Cloth", "Simple woven cotton cloth used for beginner tailoring.", "material", tier=1),
    ItemDefinition("raw_wool", "Raw Wool", "Fresh wool gathered from a sheep flock and ready for cleaning and spinning.", "material", tier=2),
    ItemDefinition("wool_yarn", "Wool Yarn", "Clean, spun wool yarn ready for weaving.", "material", tier=2),
    ItemDefinition("wool_cloth", "Wool Cloth", "Warm woven wool cloth used for sturdy tailored gear.", "material", tier=2),
    ItemDefinition("silk_cocoons", "Silk Cocoons", "Harvested silkworm cocoons containing fine natural filament.", "material", tier=3),
    ItemDefinition("silk_thread", "Silk Thread", "Fine silk filament carefully reeled into usable thread.", "material", tier=3),
    ItemDefinition("silk_cloth", "Silk Cloth", "Smooth, lightweight cloth woven from silk thread.", "material", tier=3),
    ItemDefinition("moonflax_fiber", "Moonflax Fiber", "Pale high-altitude fiber harvested from Moonflax.", "material", tier=4),
    ItemDefinition("moon_thread", "Moon Thread", "Fine thread spun from pale Moonflax fiber.", "material", tier=4),
    ItemDefinition("moonweave_cloth", "Moonweave Cloth", "Elegant pale cloth with a soft moonlit sheen.", "material", tier=4),
    ItemDefinition("raw_spidersilk", "Raw Spidersilk", "Strong, sticky silk carefully harvested from a giant spider nest.", "material", tier=5),
    ItemDefinition("spidersilk_thread", "Spidersilk Thread", "Cleaned and spun giant-spider silk of exceptional tensile strength.", "material", tier=5),
    ItemDefinition("spidersilk_cloth", "Spidersilk Cloth", "Light but exceptionally strong cloth woven from giant-spider silk.", "material", tier=5),
    ItemDefinition("ghostmoss_fiber", "Ghostmoss Fiber", "Pale fibrous moss harvested from ancient places of death.", "material", tier=6),
    ItemDefinition("ghost_thread", "Ghost Thread", "Fine, colorless thread spun from prepared Ghostmoss fiber.", "material", tier=6),
    ItemDefinition("ghostweave_cloth", "Ghostweave Cloth", "Quiet, pale funerary cloth that seems almost weightless in the hand.", "material", tier=6),
    ItemDefinition("astral_bloom_fiber", "Astral Bloom Fiber", "Extremely rare resilient fiber gathered from Astral Blooms.", "material", tier=7),
    ItemDefinition("astral_thread", "Astral Thread", "Masterwork thread spun from rare Astral Bloom fiber.", "material", tier=7),
    ItemDefinition("astralweave_cloth", "Astralweave Cloth", "The rare signature textile of Astralis, reserved for master Tailors.", "material", tier=7),
    ItemDefinition("greenleaf", "Greenleaf", "A common medicinal herb used in beginner Alchemy.", "herb", tier=1),
    ItemDefinition("bitterroot", "Bitterroot", "A sharp medicinal root valued in simple antidotes and remedies.", "herb", tier=1),
    ItemDefinition("lavender_blossom", "Lavender Blossom", "An aromatic flower used for essential oils and perfumes.", "herb", tier=1),
    ItemDefinition("wildflower", "Wildflower", "A hardy roadside bloom picked from one of Astralis's healthy wild patches.", "flora", tier=0),
    ItemDefinition("marsh_bloom", "Marsh Bloom", "A small pale wetland flower picked carefully from among the reeds.", "flora", tier=0),
    ItemDefinition("glowcap", "Glowcap", "A dim fungal cap gathered from a healthy damp-stone cluster.", "flora", tier=0),
    ItemDefinition("spring_water", "Spring Water", "Clean water used as a neutral base for simple potions.", "alchemical_reagent", tier=1),
    ItemDefinition("grain_alcohol", "Grain Alcohol", "Strong neutral alcohol used as a solvent, tincture base, and perfume carrier.", "alchemical_reagent", tier=1),
    ItemDefinition("bone_chips", "Bone Chips", "Small cleaned fragments of bone sold cheaply as a common Necromancer summoning catalyst.", "necromantic_reagent", tier=1),
    ItemDefinition("lavender_essential_oil", "Lavender Essential Oil", "Concentrated aromatic oil distilled from lavender blossoms.", "alchemical_reagent", tier=1),
    ItemDefinition("iron_ore", "Iron Ore", "Common raw ore mined from iron veins.", "material", tier=1),
    ItemDefinition("iron_ingot", "Iron Ingot", "Processed iron ready for forging.", "material", tier=1),
    ItemDefinition("coal", "Coal", "Carbon-rich fuel used to turn worked iron into steel.", "material", tier=1),
    ItemDefinition("steel_ingot", "Steel Ingot", "Refined iron hardened with coal.", "material", tier=2),
    ItemDefinition("cobalt_ore", "Cobalt Ore", "Dense blue-gray ore from deeper deposits.", "material", tier=3),
    ItemDefinition("cobalt_ingot", "Cobalt Ingot", "Refined cobalt ready for accomplished smithwork.", "material", tier=3),
    ItemDefinition("moonsilver_ore", "Moonsilver Ore", "Pale high-altitude ore used to alloy Moonsteel.", "material", tier=4),
    ItemDefinition("moonsteel_ingot", "Moonsteel Ingot", "Steel folded with rare Moonsilver.", "material", tier=4),
    ItemDefinition("emberite_ore", "Emberite Ore", "Dark ore that remains strangely warm to the touch.", "material", tier=5),
    ItemDefinition("emberite_ingot", "Emberite Ingot", "Heat-loving Emberite refined for advanced smithwork.", "material", tier=5),
    ItemDefinition("stariron_ore", "Stariron Ore", "Meteoric metal recovered from ancient impact deposits.", "material", tier=6),
    ItemDefinition("stariron_ingot", "Stariron Ingot", "Dense refined metal born beyond Astralis.", "material", tier=6),
    ItemDefinition("astralite_ore", "Astralite Ore", "Extremely rare native ore from dangerous endgame deposits.", "material", tier=7),
    ItemDefinition("astralite_ingot", "Astralite Ingot", "The signature masterwork metal of Astralis.", "material", tier=7),
)

_EQUIPMENT_ITEMS = tuple(
    item
    for tier in METAL_TIERS
    for item in _equipment_items_for_tier(
        metal_key=tier.key,
        metal_name=tier.name,
        tier=tier.tier,
    )
)

def _tailoring_items_for_tier(tier: TextileTierDefinition) -> tuple[ItemDefinition, ...]:
    """Create baseline hood/tunic gear for each textile tier.

    Stats are provisional and intentionally straightforward. Named drops, deity
    items, class restrictions, and rare scripted effects can later break this
    baseline pattern.
    """

    return (
        ItemDefinition(
            f"{tier.key}_hood",
            f"{tier.name} Hood",
            f"A tier {tier.tier} hood sewn from {tier.name.lower()} cloth.",
            "equipment",
            EquipmentItem(
                f"{tier.name} Hood",
                "head",
                armor_class=max(1, tier.tier),
                stat_bonuses=CharacterStats(mind=max(0, tier.tier - 1)),
            ),
            tier=tier.tier,
        ),
        ItemDefinition(
            f"{tier.key}_tunic",
            f"{tier.name} Tunic",
            f"A tier {tier.tier} tunic sewn from {tier.name.lower()} cloth.",
            "equipment",
            EquipmentItem(
                f"{tier.name} Tunic",
                "body",
                armor_class=max(1, tier.tier),
                stat_bonuses=CharacterStats(love=max(0, tier.tier - 1), hp=tier.tier),
            ),
            tier=tier.tier,
        ),
    )


_TAILORING_ITEMS: tuple[ItemDefinition, ...] = tuple(
    item for tier in TEXTILE_TIERS for item in _tailoring_items_for_tier(tier)
)

_ALCHEMY_ITEMS: tuple[ItemDefinition, ...] = (
    ItemDefinition(
        "minor_healing_potion",
        "Minor Healing Potion",
        "A simple green herbal potion that restores a modest amount of health.",
        "consumable",
        consumable=ConsumableEffect(use_mode="drink", heal_hp=15, effect_tags=("healing",)),
        tier=1,
    ),
    ItemDefinition(
        "lesser_antidote",
        "Lesser Antidote",
        "A bitter herbal preparation used to counter a mild poison.",
        "consumable",
        consumable=ConsumableEffect(use_mode="drink", effect_tags=("cleanse_minor_poison",)),
        tier=1,
    ),
    ItemDefinition(
        "greenleaf_tincture",
        "Greenleaf Tincture",
        "Greenleaf steeped in alcohol; less direct than a potion but useful as a portable herbal preparation.",
        "consumable",
        consumable=ConsumableEffect(use_mode="drink", heal_hp=8, effect_tags=("tincture", "healing")),
        tier=1,
    ),
    ItemDefinition(
        "lavender_perfume",
        "Lavender Perfume",
        "A light fragrance carried in alcohol and scented with concentrated lavender oil.",
        "consumable",
        consumable=ConsumableEffect(
            use_mode="apply",
            temporary_stat_bonuses=CharacterStats(grace=1),
            duration_ticks=60,
            effect_tags=("perfume", "pleasant_scent"),
        ),
        tier=1,
    ),
)

ITEMS: tuple[ItemDefinition, ...] = _MATERIAL_ITEMS + _EQUIPMENT_ITEMS + _TAILORING_ITEMS + _ALCHEMY_ITEMS
ITEMS_BY_KEY = {item.key: item for item in ITEMS}


def _smelting_recipe_for_tier(tier: MetalTierDefinition) -> CraftingRecipe:
    if tier.key == "steel":
        materials = (
            MaterialRequirement("iron_ingot", 1),
            MaterialRequirement("coal", 1),
        )
    elif tier.key == "moonsteel":
        materials = (
            MaterialRequirement("steel_ingot", 1),
            MaterialRequirement("moonsilver_ore", 1),
        )
    else:
        assert tier.raw_material_key is not None
        materials = (MaterialRequirement(tier.raw_material_key, 2),)

    return CraftingRecipe(
        key=f"smelt_{tier.key}_ingot",
        trade_skill_key="blacksmithing",
        output_item_key=tier.ingot_key,
        minimum_skill=tier.blacksmithing_skill,
        high_skill_quality_threshold=tier.blacksmithing_skill + 30,
        materials=materials,
        output_quantity=1,
        station_key="forge",
        description=f"Process materials into a {tier.name} Ingot.",
        design_status="locked_progression_provisional_tuning",
    )


def _gear_recipes_for_tier(tier: MetalTierDefinition) -> tuple[CraftingRecipe, ...]:
    base = tier.blacksmithing_skill
    quality = base + 35
    return (
        CraftingRecipe(
            key=f"forge_{tier.key}_dagger",
            trade_skill_key="blacksmithing",
            output_item_key=f"{tier.key}_dagger",
            minimum_skill=base,
            high_skill_quality_threshold=quality,
            materials=(MaterialRequirement(tier.ingot_key, 1),),
            station_key="forge",
            description=f"Forge a {tier.name} Dagger.",
            design_status="locked_progression_provisional_tuning",
        ),
        CraftingRecipe(
            key=f"forge_{tier.key}_sword",
            trade_skill_key="blacksmithing",
            output_item_key=f"{tier.key}_sword",
            minimum_skill=base + 5,
            high_skill_quality_threshold=quality + 5,
            materials=(MaterialRequirement(tier.ingot_key, 2),),
            station_key="forge",
            description=f"Forge a {tier.name} Sword.",
            design_status="locked_progression_provisional_tuning",
        ),
        CraftingRecipe(
            key=f"forge_{tier.key}_helmet",
            trade_skill_key="blacksmithing",
            output_item_key=f"{tier.key}_helmet",
            minimum_skill=base + 5,
            high_skill_quality_threshold=quality + 5,
            materials=(MaterialRequirement(tier.ingot_key, 2),),
            station_key="forge",
            description=f"Forge a {tier.name} Helmet.",
            design_status="locked_progression_provisional_tuning",
        ),
        CraftingRecipe(
            key=f"forge_{tier.key}_breastplate",
            trade_skill_key="blacksmithing",
            output_item_key=f"{tier.key}_breastplate",
            minimum_skill=base + 10,
            high_skill_quality_threshold=quality + 10,
            materials=(MaterialRequirement(tier.ingot_key, 4),),
            station_key="forge",
            description=f"Forge a {tier.name} Breastplate.",
            design_status="locked_progression_provisional_tuning",
        ),
    )


# Complete authored baseline metal ladder. Rare named drops, race/class pieces,
# enchantments, and masterwork effects will sit on top of this straightforward
# stat-based progression rather than replacing it.
BLACKSMITHING_RECIPES: tuple[CraftingRecipe, ...] = tuple(
    recipe
    for tier in METAL_TIERS
    for recipe in (_smelting_recipe_for_tier(tier), *_gear_recipes_for_tier(tier))
)
BLACKSMITHING_RECIPES_BY_KEY = {recipe.key: recipe for recipe in BLACKSMITHING_RECIPES}

# Full baseline Tailoring ladder. The early materials are familiar; later
# textiles become increasingly specific to Astralis. Quantities and raw stats
# are provisional tuning while the progression identity/order is authored.
def _tailoring_recipes_for_tier(tier: TextileTierDefinition) -> tuple[CraftingRecipe, ...]:
    quality = tier.tailoring_skill + 30

    if tier.key == "cotton":
        spin_key = "spin_cotton_thread"
        weave_key = "weave_cotton_cloth"
        raw_quantity = 2
        thread_output_quantity = 2
    elif tier.key == "wool":
        spin_key = "spin_wool_yarn"
        weave_key = "weave_wool_cloth"
        raw_quantity = 2
        thread_output_quantity = 2
    elif tier.key == "silk":
        spin_key = "reel_silk_thread"
        weave_key = "weave_silk_cloth"
        raw_quantity = 2
        thread_output_quantity = 2
    else:
        spin_key = f"spin_{tier.key}_thread"
        weave_key = f"weave_{tier.key}_cloth"
        raw_quantity = 2
        thread_output_quantity = 2

    return (
        CraftingRecipe(
            key=spin_key,
            trade_skill_key="tailoring",
            output_item_key=tier.thread_item_key,
            minimum_skill=tier.tailoring_skill,
            high_skill_quality_threshold=quality,
            materials=(MaterialRequirement(tier.raw_material_key, raw_quantity),),
            output_quantity=thread_output_quantity,
            station_key="loom",
            description=f"Prepare {tier.raw_material_name} into {tier.thread_item_name}.",
            design_status="locked_tailoring_progression_provisional_tuning",
        ),
        CraftingRecipe(
            key=weave_key,
            trade_skill_key="tailoring",
            output_item_key=tier.cloth_item_key,
            minimum_skill=tier.tailoring_skill,
            high_skill_quality_threshold=quality + 5,
            materials=(MaterialRequirement(tier.thread_item_key, 2),),
            output_quantity=1,
            station_key="loom",
            description=f"Weave {tier.thread_item_name} into {tier.cloth_item_name}.",
            design_status="locked_tailoring_progression_provisional_tuning",
        ),
        CraftingRecipe(
            key=f"sew_{tier.key}_hood",
            trade_skill_key="tailoring",
            output_item_key=f"{tier.key}_hood",
            minimum_skill=tier.tailoring_skill + 2,
            high_skill_quality_threshold=quality + 5,
            materials=(MaterialRequirement(tier.cloth_item_key, 1),),
            output_quantity=1,
            station_key="loom",
            description=f"Sew a {tier.name} Hood.",
            design_status="locked_tailoring_progression_provisional_tuning",
        ),
        CraftingRecipe(
            key=f"sew_{tier.key}_tunic",
            trade_skill_key="tailoring",
            output_item_key=f"{tier.key}_tunic",
            minimum_skill=tier.tailoring_skill + 3,
            high_skill_quality_threshold=quality + 10,
            materials=(MaterialRequirement(tier.cloth_item_key, 2),),
            output_quantity=1,
            station_key="loom",
            description=f"Sew a {tier.name} Tunic.",
            design_status="locked_tailoring_progression_provisional_tuning",
        ),
    )


TAILORING_RECIPES: tuple[CraftingRecipe, ...] = tuple(
    recipe for tier in TEXTILE_TIERS for recipe in _tailoring_recipes_for_tier(tier)
)
TAILORING_RECIPES_BY_KEY = {recipe.key: recipe for recipe in TAILORING_RECIPES}

# Early Alchemy is herb-first and intentionally broad: healing, poison care,
# tinctures, aromatic extraction, and perfume all share the same profession.
# Costs, thresholds, and effect strengths are provisional balance values.
ALCHEMY_RECIPES: tuple[CraftingRecipe, ...] = (
    CraftingRecipe(
        key="brew_minor_healing_potion",
        trade_skill_key="alchemy",
        output_item_key="minor_healing_potion",
        minimum_skill=0,
        high_skill_quality_threshold=25,
        materials=(MaterialRequirement("greenleaf", 2), MaterialRequirement("spring_water", 1)),
        output_quantity=1,
        station_key="mortar_and_pestle",
        description="Crush Greenleaf into a simple restorative potion.",
        design_status="locked_early_alchemy_provisional_tuning",
    ),
    CraftingRecipe(
        key="brew_lesser_antidote",
        trade_skill_key="alchemy",
        output_item_key="lesser_antidote",
        minimum_skill=5,
        high_skill_quality_threshold=30,
        materials=(
            MaterialRequirement("bitterroot", 1),
            MaterialRequirement("greenleaf", 1),
            MaterialRequirement("spring_water", 1),
        ),
        output_quantity=1,
        station_key="mortar_and_pestle",
        description="Grind Bitterroot and Greenleaf into a mild antidote.",
        design_status="locked_early_alchemy_provisional_tuning",
    ),
    CraftingRecipe(
        key="prepare_greenleaf_tincture",
        trade_skill_key="alchemy",
        output_item_key="greenleaf_tincture",
        minimum_skill=8,
        high_skill_quality_threshold=35,
        materials=(MaterialRequirement("greenleaf", 1), MaterialRequirement("grain_alcohol", 1)),
        output_quantity=1,
        station_key="mortar_and_pestle",
        description="Steep prepared Greenleaf in strong alcohol to make a tincture.",
        design_status="locked_early_alchemy_provisional_tuning",
    ),
    CraftingRecipe(
        key="distill_lavender_essential_oil",
        trade_skill_key="alchemy",
        output_item_key="lavender_essential_oil",
        minimum_skill=10,
        high_skill_quality_threshold=40,
        materials=(MaterialRequirement("lavender_blossom", 3),),
        output_quantity=1,
        station_key="alchemy_table",
        description="Distill Lavender Blossoms into concentrated essential oil.",
        design_status="locked_early_alchemy_provisional_tuning",
    ),
    CraftingRecipe(
        key="blend_lavender_perfume",
        trade_skill_key="alchemy",
        output_item_key="lavender_perfume",
        minimum_skill=12,
        high_skill_quality_threshold=45,
        materials=(
            MaterialRequirement("grain_alcohol", 1),
            MaterialRequirement("lavender_essential_oil", 1),
        ),
        output_quantity=1,
        station_key="alchemy_table",
        description="Blend alcohol and Lavender Essential Oil into a light perfume.",
        design_status="locked_perfume_system_provisional_tuning",
    ),
)
ALCHEMY_RECIPES_BY_KEY = {recipe.key: recipe for recipe in ALCHEMY_RECIPES}

ALL_RECIPES = BLACKSMITHING_RECIPES + TAILORING_RECIPES + ALCHEMY_RECIPES
RECIPES_BY_KEY = {recipe.key: recipe for recipe in ALL_RECIPES}


MAX_CRAFT_DIFFICULTY_GAP = 50


def craft_success_chance(skill_value: int, trivial_skill: int) -> float:
    """Return the success chance for a completed crafting attempt.

    Once the crafter reaches the recipe trivial value the craft is guaranteed.
    Recipes more than 50 skill above the crafter are rejected before this roll.
    """

    gap = trivial_skill - skill_value
    if gap <= 0:
        return 1.0
    if gap <= 5:
        return 0.95
    if gap <= 10:
        return 0.85
    if gap <= 20:
        return 0.70
    if gap <= 30:
        return 0.50
    if gap <= 40:
        return 0.30
    if gap <= MAX_CRAFT_DIFFICULTY_GAP:
        return 0.15
    return 0.0


def craft_skillup_chance(skill_value: int, trivial_skill: int) -> float:
    """Chance that one completed attempt raises the relevant trade skill by 1."""

    gap = trivial_skill - skill_value
    if gap <= 0:
        return 0.0
    if gap <= 5:
        return 0.06
    if gap <= 10:
        return 0.12
    if gap <= 20:
        return 0.20
    if gap <= 30:
        return 0.25
    if gap <= MAX_CRAFT_DIFFICULTY_GAP:
        return 0.30
    return 0.0


def craft_time_seconds(recipe: CraftingRecipe) -> float:
    """Short deliberate channel time based on recipe material complexity."""

    material_units = sum(requirement.quantity for requirement in recipe.materials)
    return min(6.0, max(3.0, 3.0 + max(0, material_units - 1) * 0.5))


@dataclass(frozen=True, slots=True)
class CraftAttemptResult:
    success: bool
    message: str
    output_item_key: str | None = None
    output_quantity: int = 0
    high_quality: bool = False
    completed: bool = False
    skill_increased: bool = False
    new_skill_value: int | None = None
    success_chance: float = 0.0
    trivial_skill: int | None = None


def trade_skill_value(database: "Database", character_id: int, trade_skill_key: str) -> int:
    """Persisted trade-skill XP is the usable crafting skill value."""

    return database.get_trade_skill_progress(character_id, trade_skill_key)["skill_xp"]


def item_display_name(item_key: str) -> str:
    """Return the authored player-facing item name for an internal item key."""

    item = ITEMS_BY_KEY.get(item_key)
    if item is not None:
        return item.name
    return item_key.replace("_", " ").title()


def crafting_skill_feedback(
    recipe: CraftingRecipe,
    *,
    new_skill_value: int,
    skill_increased: bool,
) -> str:
    """Describe the actual result of a completed craft's skill-up roll."""

    profession_name = recipe.trade_skill_key.title()
    trivial = recipe.trivial_skill
    if skill_increased:
        return f"{profession_name} improves to {new_skill_value}."
    if new_skill_value >= trivial:
        return (
            f"No {profession_name} skill increase; current skill is {new_skill_value}. "
            "This recipe is trivial for you and can no longer raise the skill."
        )

    skillup_pct = int(round(craft_skillup_chance(new_skill_value, trivial) * 100))
    return (
        f"No {profession_name} skill increase this attempt; current skill is {new_skill_value}. "
        f"This recipe can still train you ({skillup_pct}% chance per completed craft at this skill)."
    )


def craft_recipe(
    database: "Database",
    character_id: int,
    recipe_key: str,
    *,
    station_key: str | None = None,
    success_roll: float | None = None,
    skillup_roll: float | None = None,
) -> CraftAttemptResult:
    """Resolve one completed craft.

    Validation failures do not consume materials. Once an eligible attempt
    completes, materials are consumed whether the result succeeds or fails.
    Success and skill improvement are separate rolls; failed work can still
    teach the crafter, while a recipe at or below current skill is trivial and
    can no longer grant skill.
    """

    recipe = RECIPES_BY_KEY.get(recipe_key)
    if recipe is None:
        return CraftAttemptResult(False, "Unknown recipe.")

    if recipe.station_key is not None and station_key != recipe.station_key:
        return CraftAttemptResult(False, f"Requires a {recipe.station_key}.")

    skill_value = trade_skill_value(database, character_id, recipe.trade_skill_key)
    trivial = recipe.trivial_skill
    if not recipe.can_attempt(skill_value, max_gap=MAX_CRAFT_DIFFICULTY_GAP):
        return CraftAttemptResult(
            False,
            (
                f"This recipe is too difficult to attempt: {recipe.trade_skill_key} "
                f"{skill_value}, trivial {trivial}. You can attempt recipes up to "
                f"{MAX_CRAFT_DIFFICULTY_GAP} skill above you."
            ),
            trivial_skill=trivial,
        )

    missing = [
        (
            requirement,
            requirement.quantity
            - database.item_quantity(character_id, requirement.item_key),
        )
        for requirement in recipe.materials
        if database.item_quantity(character_id, requirement.item_key) < requirement.quantity
    ]
    if missing:
        text = ", ".join(
            f"{shortfall}x {item_display_name(requirement.item_key)}"
            for requirement, shortfall in missing
        )
        return CraftAttemptResult(False, f"Missing materials: {text}.", trivial_skill=trivial)

    from mud.inventory_capacity import crafting_output_fits
    if not crafting_output_fits(database, character_id, recipe):
        return CraftAttemptResult(
            False,
            "Your inventory has no room for the crafted item. Free a slot or equip a larger bag first.",
            trivial_skill=trivial,
        )

    success_chance = craft_success_chance(skill_value, trivial)
    skillup_chance = craft_skillup_chance(skill_value, trivial)
    if success_chance >= 1.0:
        crafted = True
    else:
        resolved_success_roll = random.random() if success_roll is None else float(success_roll)
        crafted = resolved_success_roll < success_chance

    skill_increased = False
    if skillup_chance > 0.0:
        resolved_skillup_roll = random.random() if skillup_roll is None else float(skillup_roll)
        skill_increased = resolved_skillup_roll < skillup_chance

    high_quality = crafted and recipe.produces_high_quality_result(skill_value)
    heritage_recipe_revision = None
    if crafted:
        from mud.item_heritage import recipe_revision

        heritage_recipe_revision = recipe_revision(recipe)

    transaction_kwargs = {
        "trade_skill_key": recipe.trade_skill_key,
        "materials": recipe.materials,
        "output_item_key": recipe.output_item_key,
        "output_quantity": recipe.output_quantity,
        "skill_xp_gain": 1 if skill_increased else 0,
        "craft_succeeded": crafted,
    }
    # Lightweight content tests and third-party integrations may provide the
    # older transaction contract. Only pass heritage metadata when that method
    # explicitly supports it; the real Database does.
    from inspect import signature

    transaction_parameters = signature(database.complete_crafting_transaction).parameters
    if "heritage_recipe_key" in transaction_parameters:
        transaction_kwargs.update(
            heritage_recipe_key=recipe.key if crafted else None,
            heritage_recipe_revision=heritage_recipe_revision,
            heritage_high_quality=high_quality,
        )

    committed = database.complete_crafting_transaction(
        character_id,
        **transaction_kwargs,
    )
    if not committed:
        return CraftAttemptResult(
            False,
            "The required materials were no longer available.",
            trivial_skill=trivial,
        )

    new_skill = skill_value + (1 if skill_increased else 0)
    learning = " " + crafting_skill_feedback(
        recipe,
        new_skill_value=new_skill,
        skill_increased=skill_increased,
    )

    if crafted:
        message = f"Crafted {recipe.output_quantity}x {item_display_name(recipe.output_item_key)}." + learning
    else:
        message = "The crafting attempt fails, consuming the materials." + learning

    return CraftAttemptResult(
        crafted,
        message,
        output_item_key=recipe.output_item_key if crafted else None,
        output_quantity=recipe.output_quantity if crafted else 0,
        high_quality=high_quality,
        completed=True,
        skill_increased=skill_increased,
        new_skill_value=new_skill,
        success_chance=success_chance,
        trivial_skill=trivial,
    )

def gather_node(
    database: "Database",
    character_id: int,
    node: ResourceNodeState,
) -> str | None:
    """Gather from any authored resource node using that node's gathering skill."""

    skill_key = node.definition.gathering_skill_key
    skill_value = trade_skill_value(database, character_id, skill_key) if skill_key else 0
    output = node.gather(skill_value=skill_value)
    if output is None:
        return None
    database.add_item(character_id, output, 1)
    if skill_key:
        database.record_trade_skill_use(character_id, skill_key, 1)
    return output


def mine_node(
    database: "Database",
    character_id: int,
    node: ResourceNodeState,
) -> str | None:
    """Backward-compatible mining helper; gathering now supports non-mining nodes too."""

    return gather_node(database, character_id, node)
