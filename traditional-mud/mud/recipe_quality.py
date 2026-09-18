from __future__ import annotations

from dataclasses import replace

import mud.crafting as crafting
from mud.gear import MaterialRequirement


def _materials(*pairs: tuple[str, int]) -> tuple[MaterialRequirement, ...]:
    return tuple(MaterialRequirement(key, quantity) for key, quantity in pairs)


def _replace_recipe_everywhere(recipe_key: str, **changes) -> None:
    recipe = crafting.RECIPES_BY_KEY.get(recipe_key)
    if recipe is None:
        return

    updated = replace(recipe, **changes)
    crafting.RECIPES_BY_KEY[recipe_key] = updated
    crafting.ALL_RECIPES = tuple(
        updated if existing.key == recipe_key else existing
        for existing in crafting.ALL_RECIPES
    )

    registry_names = (
        ("BLACKSMITHING_RECIPES", "BLACKSMITHING_RECIPES_BY_KEY"),
        ("TAILORING_RECIPES", "TAILORING_RECIPES_BY_KEY"),
        ("ALCHEMY_RECIPES", "ALCHEMY_RECIPES_BY_KEY"),
    )
    for tuple_name, dict_name in registry_names:
        recipes = getattr(crafting, tuple_name, ())
        if any(existing.key == recipe_key for existing in recipes):
            setattr(
                crafting,
                tuple_name,
                tuple(updated if existing.key == recipe_key else existing for existing in recipes),
            )
        mapping = getattr(crafting, dict_name, None)
        if isinstance(mapping, dict) and recipe_key in mapping:
            mapping[recipe_key] = updated


def apply_recipe_semantic_quality() -> None:
    """Correct the remaining recipes whose ingredients read like loot rotation.

    Older content waves deliberately forced cross-region materials together to
    stimulate trade. That was useful economically, but a few recipes ended up
    consuming objects that had no believable physical role in the finished item.
    This pass keeps the stable recipe/output keys while making the construction
    logic legible to a player.
    """

    _replace_recipe_everywhere(
        "sew_briarheart_mantle",
        materials=_materials(
            ("cotton_cloth", 1),
            ("rough_hide", 1),
            ("tough_sinew", 1),
        ),
        description=(
            "Sew a rugged cotton mantle over a hide shoulder yoke and bind the "
            "stress points with tough sinew."
        ),
        design_status="semantic_material_audit",
    )

    _replace_recipe_everywhere(
        "sew_resonant_vestments",
        materials=_materials(
            ("cotton_cloth", 2),
            ("cotton_thread", 1),
            ("gloamworks_resonant_cog", 1),
        ),
        description=(
            "Tailor layered cotton vestments and mount the Resonant Cog as a "
            "small breast focus rather than treating it as fabric."
        ),
        design_status="semantic_material_audit",
    )

    _replace_recipe_everywhere(
        "forge_bastion_lineholder_shield",
        materials=_materials(
            ("lineholder_shield", 1),
            ("lineholder_commission_plate", 1),
            ("gravewatch_old_garrison_iron", 2),
            ("blackreed_iron_fitting", 1),
        ),
        description=(
            "Rebuild the Lineholder Shield with old garrison plate and a heavy "
            "Blackreed brace; the commission plate marks the authorized pattern."
        ),
        design_status="semantic_material_audit",
    )

    _replace_recipe_everywhere(
        "forge_clockglass_circlet",
        materials=_materials(
            ("coldglass_circlet", 1),
            ("focus_commission_plate", 1),
            ("density_broken_observatory_minor_material", 1),
            ("drowned_brass_scrap", 1),
        ),
        description=(
            "Rework the Coldglass Circlet with a fine astrolabe cog and reclaimed "
            "brass so its moving focus ring has an actual mechanism."
        ),
        design_status="semantic_material_audit",
    )

    _replace_recipe_everywhere(
        "sew_floodroot_mantle",
        materials=_materials(
            ("briarheart_mantle", 1),
            ("steward_commission_plate", 1),
            ("drowned_brass_scrap", 1),
            ("bitterroot", 2),
        ),
        description=(
            "Upgrade the Briarheart Mantle with a reclaimed brass clasp and a "
            "boiled Bitterroot treatment worked into the cloth as a dark river dye."
        ),
        design_status="semantic_material_audit",
    )

    _replace_recipe_everywhere(
        "sew_bellwarden_vestments",
        materials=_materials(
            ("resonant_vestments", 1),
            ("care_commission_plate", 1),
            ("gloamworks_resonant_cog", 1),
            ("silk_thread", 1),
        ),
        description=(
            "Refit the Resonant Vestments with a second tuned cog and silk "
            "suspension stitching so the metal focus hangs without tearing cloth."
        ),
        design_status="semantic_material_audit",
    )

    _replace_recipe_everywhere(
        "forge_grave_regent_wand",
        materials=_materials(
            ("regent_bone_wand", 1),
            ("gravework_commission_plate", 1),
            ("gravewatch_old_garrison_iron", 1),
            ("drowned_brass_scrap", 1),
            ("bone_chips", 2),
        ),
        description=(
            "Reinforce the Regent-Bone Wand with an old-iron spine, a brass "
            "ferrule, and fresh bone inlay; the commission plate authorizes the pattern."
        ),
        design_status="semantic_material_audit",
    )
