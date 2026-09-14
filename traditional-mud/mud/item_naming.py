from __future__ import annotations

from dataclasses import dataclass, replace

import mud.crafting as crafting
import mud.stats as stats


@dataclass(frozen=True, slots=True)
class ItemPresentation:
    name: str
    description: str


# Persistent inventory keys are deliberately unchanged.  These are presentation
# corrections for old development-era objects whose keys are already present in
# saved characters, recipes, loot tables, and equipment rows.
AUTHORED_ITEM_PRESENTATIONS: dict[str, ItemPresentation] = {
    "starter_weapon": ItemPresentation(
        "Wayfarer's Iron",
        "A short, single-edged iron blade with a leather-wrapped grip and a maker's stamp worn nearly flat. It is plain road gear: made to survive rain, bad scabbards, and the first miles beyond home.",
    ),
    "brute_training_harness": ItemPresentation(
        "Lineholder's Harness",
        "Broad oxhide straps and riveted iron plates protect the ribs, shoulders, and spine without pretending to be parade armor. Its weight teaches the wearer to plant their feet and hold a line.",
    ),
    "density_small_saint_minor_material": ItemPresentation(
        "Unshriven Bell Clapper",
        "A soot-darkened bronze clapper taken from the Unshriven Sexton's ruined bellwork. It gives a low, stubborn note when struck against stone.",
    ),
    "density_small_saint_major_material": ItemPresentation(
        "Saintless Emberglass",
        "A thumb-sized piece of smoky glass recovered from the Saintless Keeper. A dull orange point remains trapped inside it even after the chapel has gone cold.",
    ),
    "density_salt_king_minor_material": ItemPresentation(
        "Steward's Brinehook",
        "A hooked brass fitting from the Pickled Steward's preserving rig, green at the edges but still sharp enough to catch cloth and cord.",
    ),
    "density_salt_king_major_material": ItemPresentation(
        "Salt-King's Brineheart",
        "A fist-sized knot of mineralized salt and old brass from the deepest larder machinery. Moisture beads across its surface no matter how dry the room becomes.",
    ),
    "density_red_door_minor_material": ItemPresentation(
        "Velvet Lockplate",
        "A narrow black lockplate backed with faded red velvet, removed from the Locksmith's private mechanism. Fine tool marks crowd its hidden face.",
    ),
    "density_red_door_major_material": ItemPresentation(
        "Custodian's Red Key",
        "A heavy key lacquered the same impossible red as the Cellars' famous door. Its teeth are asymmetrical enough that no ordinary lock should accept it.",
    ),
    "density_broken_observatory_minor_material": ItemPresentation(
        "Blind Astrolabe Cog",
        "A delicate toothed wheel from the Blind Astrolabe, engraved with star marks that continue across surfaces no viewer was meant to see.",
    ),
    "density_broken_observatory_major_material": ItemPresentation(
        "Fallen-Moon Lensglass",
        "A curved shard of dark lensglass left by the Watcher of the Fallen Moon. Tilted toward the sky, it catches one pale point that is not where any visible star stands.",
    ),
    "density_rootcourt_minor_material": ItemPresentation(
        "Hollow Antler Splint",
        "A pale antler splint from Hollow Antler, light as dry reed and resonant when tapped. The inside is threaded with fine root fibers instead of marrow.",
    ),
    "density_rootcourt_major_material": ItemPresentation(
        "Rootcourt Heartwood",
        "A dense twist of living-dark heartwood recovered from the Rootcourt Queen's chamber. Fresh-cut rings tighten and loosen as if remembering the shape of a tree.",
    ),
    "density_brass_lung_minor_material": ItemPresentation(
        "Bellows Valve-Tongue",
        "A heat-blued valve tongue from Foreman Bellows' pressure gear. Its edge is polished bright where years of steam forced it open and shut.",
    ),
    "density_brass_lung_major_material": ItemPresentation(
        "Furnace-Breath Clinker",
        "A black metallic clinker fused inside Furnace Breath, surprisingly light and warm to the touch. Tiny brass bubbles gleam through its broken surface.",
    ),
    "density_white_room_minor_material": ItemPresentation(
        "Guestless Chair Splinter",
        "A perfectly white sliver from the Chair Without Guest. One end shows fresh grain; the other is smooth as if generations of hands had worried it down.",
    ),
    "density_white_room_major_material": ItemPresentation(
        "Curator's White Porcelain",
        "A clean porcelain shard from the White Curator, unmarked except for a hair-thin gray line that bends when viewed from the corner of the eye.",
    ),
}


def _rename_definition(item):
    presentation = AUTHORED_ITEM_PRESENTATIONS.get(item.key)
    if presentation is None:
        return item
    equipment = item.equipment
    if equipment is not None:
        equipment = replace(equipment, name=presentation.name)
    return replace(
        item,
        name=presentation.name,
        description=presentation.description,
        equipment=equipment,
    )


def install_authored_item_names() -> None:
    """Replace development labels without migrating any persistent item keys.

    Content modules register items during production assembly, so this pass runs
    after all world/item installers have finished.  Recipes, inventories, loot,
    equipped rows, and old characters continue to reference the exact same keys.
    """

    renamed_by_key: dict[str, object] = {}
    normalized = []
    for item in crafting.ITEMS:
        renamed = _rename_definition(item)
        normalized.append(renamed)
        renamed_by_key[item.key] = renamed
    crafting.ITEMS = tuple(normalized)

    # Some later content registers directly in the dictionary. Keep those entries
    # in sync as well, while preserving the dictionary object imported elsewhere.
    for key, item in tuple(crafting.ITEMS_BY_KEY.items()):
        crafting.ITEMS_BY_KEY[key] = renamed_by_key.get(key, _rename_definition(item))

    # Keep the older stat-module constants coherent for code/tests that still read
    # them directly. They are not persistent records, so changing their display
    # names has no save migration cost.
    starter = AUTHORED_ITEM_PRESENTATIONS["starter_weapon"]
    stats.STARTER_WEAPON = replace(stats.STARTER_WEAPON, name=starter.name)

    harness = AUTHORED_ITEM_PRESENTATIONS["brute_training_harness"]
    stats.BRUTE_STARTER_ARMOR = replace(stats.BRUTE_STARTER_ARMOR, name=harness.name)
    stats.STARTER_ARMOR_BY_CLASS["brute"] = stats.BRUTE_STARTER_ARMOR
