from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RaceDefinition:
    key: str
    name: str
    description: str
    lore: tuple[str, ...] = ()
    starting_region: str | None = None
    social_profile: str | None = None
    passive_name: str | None = None
    passive_description: str | None = None
    regen_bonus_per_tick: int = 0
    needs_food: bool = True
    needs_drink: bool = True
    needs_sleep: bool = True
    needs_breath: bool = True
    poison_resistance: str = "normal"
    disease_resistance: str = "normal"
    normal_healing_magic: bool = True
    ability_name: str | None = None
    ability_description: str | None = None
    design_status: str = "locked"


@dataclass(frozen=True, slots=True)
class ClassDefinition:
    key: str
    name: str
    description: str
    abilities_customizable: bool = False
    early_game_identity: str = ""
    endgame_identity: str = ""
    class_passives: tuple[str, ...] = ()
    equipment_identity: str = ""
    requires_deity_path: bool = False
    allows_shapeshifting: bool = False
    design_status: str = "foundation"


# Eight-race launch roster. Every race uses the same basic humanoid equipment
# anatomy, and every race/class combination is legal.
RACES: tuple[RaceDefinition, ...] = (
    RaceDefinition(
        key="human",
        name="Human",
        description=(
            "Rare Astralis-born descendants of dimensional travelers from legendary Earth. "
            "Native peoples often call them Demons, an image their kingdom deliberately made its own."
        ),
        lore=(
            "Humans intentionally crossed from Earth several centuries ago while experimenting with dimensional travel.",
            "No known route back to Earth remains, and modern humans are native-born citizens of Astralis.",
            "Almost all Earth culture has been lost; surviving Earth objects are rare historical artifacts.",
            "Humans are the least numerous playable people and maintain one large, relatively insular kingdom.",
            "The kingdom embraced the outsider label 'Demon' generations ago, using demonic imagery in its aesthetics and identity.",
            "Their closest major neighbors are the dwarves.",
        ),
        starting_region="human_kingdom",
        social_profile="rare_outsiders_called_demons",
        passive_name="Fast Learner",
        passive_description=(
            "Humans improve practiced abilities faster than other races. The exact tuning multiplier is intentionally not set yet."
        ),
    ),
    RaceDefinition(
        key="forest_elf",
        name="Forest Elf",
        description=(
            "Isolated woodland elves governed by Druidic Circles. Their connection to nature is only slightly magical, "
            "and they regard themselves as the only true elves."
        ),
        lore=(
            "Forest Elves live mainly in isolated towns within a vast forest.",
            "They have roughly human lifespans, averaging around eighty years.",
            "They are somewhat more graceful and attractive than humans on average, with long pointed ears.",
            "Their political life is organized through Druidic Circles rather than hereditary monarchy.",
            "They insist that they are simply 'Elves' and deny that Moon Elves are true elves at all.",
            "Their starting experience begins beautiful and comfortable, then gradually introduces danger.",
        ),
        starting_region="great_elf_forest",
        social_profile="isolated_and_insular",
    ),
    RaceDefinition(
        key="moon_elf",
        name="Moon Elf",
        description=(
            "Lavender-grey elves with oversized eyes and no visible sclera. Their lost origins and ancient lunar culture "
            "make them visibly unusual, though they are long-established on Astralis."
        ),
        lore=(
            "Their true origin is lost to time; some traditions claim they arrived from beyond Astralis without technology.",
            "They have normal hair and otherwise familiar elven humanoid anatomy.",
            "Their civilization is ancient, mystical, elegant, and deeply tied to Astralis's moon.",
            "They are emotionally familiar rather than alien and are broadly accepted by other races.",
            "They resent Forest Elf claims that they are not real elves.",
            "Like Forest Elves, they insist that they are simply 'Elves'; 'Moon Elf' is an outsider/player-facing label.",
            "Their high-altitude homeland places their cities among mountain peaks closer to the moonlit sky.",
        ),
        starting_region="moon_peaks",
        social_profile="accepted_but_elven_rivalry",
    ),
    RaceDefinition(
        key="dwarf",
        name="Dwarf",
        description=(
            "Traditional dwarves from vast steam-powered mountain settlements spanning underground cities and above-ground towns. "
            "Their culture is bureaucratic, cosmopolitan, and obsessed with craftsmanship."
        ),
        lore=(
            "Dwarven industry is roughly one step beyond sophisticated clockwork and is powered primarily by steam.",
            "Engineering is a cultural discipline, not an innate racial gift.",
            "Dwarves are generally four to five feet tall and retain familiar broad-built fantasy appearances.",
            "Power is shared among wealthy trade houses and strong labor unions.",
            "Their cities are among the most socially mixed places on Astralis.",
            "Classic mining, stonework, and metalwork remain present but are not the sole focus of dwarven identity.",
            "The starting experience is a functioning industrial city of workshops, foundries, union halls, freight routes, lifts, and steam infrastructure.",
        ),
        starting_region="dwarven_mountain_industry",
        social_profile="cosmopolitan_trade_power",
    ),
    RaceDefinition(
        key="goblin",
        name="Goblin",
        description=(
            "Green-skinned, sharp-toothed scavengers from swamp clans and the great Junk City. Goblins are distrusted but indispensable "
            "traders, salvagers, repairers, couriers, and fixers."
        ),
        lore=(
            "Goblins average around five feet tall, with green skin, large ears, sharp teeth, and long noses.",
            "They are somewhat weaker than most races but are not frail.",
            "Many loosely connected clans occupy swamp towns, while nearly all regard the Junk City as their metropolitan home.",
            "Goblin society is highly transactional and shaped by gangs, merchant families, inventors, and fixers.",
            "They excel at salvaging, repairing, and repurposing rather than inventing entirely new technologies.",
            "Their workmanship is ugly, patched, improvised, and surprisingly effective rather than randomly unreliable.",
            "They are treated as a distrusted underclass, yet other peoples routinely trade and work with them.",
            "Goblins sometimes recover Earth artifacts and sell them to humans for preservation and study.",
            "Goblin culture is mildly irreverent without becoming parody, and Goblins are proud of their name.",
            "Their starting experience is busy, noisy, dense, and full of interactive markets, salvage, traffic, shortcuts, and deals.",
        ),
        starting_region="junk_city_and_swamps",
        social_profile="distrusted_underclass",
    ),
    RaceDefinition(
        key="troll",
        name="Troll",
        description=(
            "Ancient seven-foot green-skinned nomads from deep forests, tundra, and scattered strongholds. Trolls are formidable hunters "
            "and warriors whose average intelligence is routinely underestimated."
        ),
        lore=(
            "Trolls are among the oldest peoples on Astralis and have no single centralized homeland.",
            "They live in rough but organized nomadic tribes and strongholds led by chieftains and priests.",
            "Deep-forest trolls are common; Snow Trolls are a tundra regional culture, not a separate race.",
            "Strength comes naturally to trolls, but their culture does not treat strength as a moral virtue or obsession.",
            "They are skilled hunters, warriors, and animal handlers.",
            "Other races often stereotype trolls as stupid despite their average intelligence, leaving many trolls bitter about outsider distrust.",
            "Their culture is brutal and intimidating in presentation, and their starting experience is harsh and dangerous immediately.",
        ),
        starting_region="troll_strongholds",
        social_profile="distrusted_and_stereotyped",
        passive_name="Regeneration",
        passive_description="Trolls recover 1 additional hit point whenever normal server regeneration occurs.",
        regen_bonus_per_tick=1,
    ),
    RaceDefinition(
        key="undead",
        name="Undead",
        description=(
            "Reanimated dead who retain memories of their former lives. Nearly skeletal but not rotting, they maintain a gloomy, "
            "death-obsessed civilization centered on a vast underground necropolis beneath a desolate desert."
        ),
        lore=(
            "Every Undead was once a living person and may have originated from any of Astralis's other peoples.",
            "They remember their former lives and are truly dead rather than merely death-touched.",
            "Their bodies are almost skeletal but preserved enough to function normally; they are not decaying corpses.",
            "They do not need food, drink, sleep, or breath, though they eventually deteriorate and die permanently.",
            "Their main civilization is a huge underground necropolis beneath a desolate desert, with ruined Undead kingdoms scattered elsewhere.",
            "Society is gloomy and death-obsessed, governed by priest-kings and ancient houses.",
            "Necromancy is common, and their dominant religion teaches that death leads to reanimation.",
            "Other races generally fear them. Most Undead regard reanimation as a gift, though some consider it a curse.",
            "Ordinary healing magic works normally on them, while poison and disease affect them less strongly than living peoples.",
            "Their starting experience should be quiet, eerie, and funerary rather than chaotic.",
        ),
        starting_region="desert_necropolis",
        social_profile="feared",
        needs_food=False,
        needs_drink=False,
        needs_sleep=False,
        needs_breath=False,
        poison_resistance="reduced_effect",
        disease_resistance="reduced_effect",
        normal_healing_magic=True,
    ),
    RaceDefinition(
        key="sporekin",
        name="Sporekin",
        description=(
            "Wise humanoid fungal beings whose civilization extends above and below ground, with most of their society hidden in vast "
            "underground networks unseen by other peoples."
        ),
        lore=(
            "Sporekin are fully humanoid in equipment anatomy despite their fungal biology.",
            "Most Sporekin civilization exists underground, with a smaller surface presence in fungal groves and settlements.",
            "They reproduce through spores rather than ordinary humanoid reproduction.",
            "They see themselves as guides to the other peoples of Astralis.",
            "Their society participates in a shared consciousness, giving the culture an unusual collective dimension.",
            "Their natural regeneration is stronger than that of trolls.",
        ),
        starting_region="sporekin_underways",
        social_profile="wise_hidden_guides",
        passive_name="Deep Regeneration",
        passive_description="Sporekin recover 2 additional hit points whenever normal server regeneration occurs.",
        regen_bonus_per_tick=2,
    ),
)


CLASSES: tuple[ClassDefinition, ...] = (
    ClassDefinition(
        key="brute",
        name="Brute",
        description="A warrior-like physical combat class built around tanking, threat control, and weapon damage.",
        early_game_identity=(
            "Begins with solid weapon proficiency and Taunt, then gains Heavy Strike very early."
        ),
        endgame_identity=(
            "Primary tank: maintains enemy hate, uses high-damage melee attacks, and has only a small number "
            "of defensive self-buffs. Gear and weapons are critical to success, while most major buffs come from allies."
        ),
        equipment_identity="Weapon- and gear-dependent heavy melee combatant.",
        design_status="class_arc_locked",
    ),
    ClassDefinition(
        key="wizard",
        name="Wizard",
        description="An arcane damage class focused on powerful direct spells, self-protection, and magical utility.",
        early_game_identity=(
            "Begins with Coldfire Burst, gains a minor self-protective barrier at level 2, and Arcane Bolt at level 3."
        ),
        endgame_identity=(
            "Single-target magical nuke powerhouse with world-teleport spells, self-protection, and minor control utility such as roots."
        ),
        equipment_identity="Spell-power-focused caster; protection comes primarily from magic rather than party buffs.",
        design_status="class_arc_locked",
    ),
    ClassDefinition(
        key="druid",
        name="Druid",
        description="A nature-oriented support caster combining healing, buffs, utility, and natural magic without shapeshifting.",
        early_game_identity=(
            "Can forage for natural materials, begins with a minor healing spell, and gains a castable HP buff at level 2."
        ),
        endgame_identity=(
            "Reliable secondary healer for endgame groups, with restorative magic, nature-themed buffs, wards, and control utility. "
            "Priests remain the stronger dedicated healers."
        ),
        class_passives=("Foraging",),
        equipment_identity="Support caster whose value comes from healing, buffs, and nature utility.",
        allows_shapeshifting=False,
        design_status="class_arc_locked",
    ),
    ClassDefinition(
        key="priest",
        name="Priest",
        description="The premier healing and defensive-support class, with spell paths shaped by a chosen deity.",
        early_game_identity=(
            "Chooses a deity whose path determines the Priest's authored spell and ability progression."
        ),
        endgame_identity=(
            "Prime healer: keeps groups alive, resurrects fallen allies, and supplies powerful HP and AC buffs while wearing heavy plate armor."
        ),
        equipment_identity="Heavy plate healer/support caster.",
        requires_deity_path=True,
        design_status="class_arc_locked_deities_authored",
    ),
    ClassDefinition(
        key="necromancer",
        name="Necromancer",
        description="A pet-and-decay caster built around undead servants, damage-over-time magic, and dark utility.",
        early_game_identity=(
            "Begins with Minor Life Tap at level 1, gains Raise Skeleton at level 2 using Bone Chips as a catalyst, "
            "and learns the damage-over-time spell Rot at level 3."
        ),
        endgame_identity=(
            "Commands a powerful undead pet, masters stacking rot/damage-over-time magic, gains lich-like skeletal transformation, "
            "and carries distinctive necromantic utility."
        ),
        equipment_identity="Caster whose power is split between personal decay magic and an undead pet.",
        design_status="class_arc_locked",
    ),
)


RACES_BY_KEY = {race.key: race for race in RACES}
CLASSES_BY_KEY = {character_class.key: character_class for character_class in CLASSES}
