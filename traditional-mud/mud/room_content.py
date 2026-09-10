from __future__ import annotations

from mud.room_engine import (
    DescriptionLayer,
    ExitDefinition,
    FeatureDefinition,
    RoomAugmentation,
    ViewCondition,
)
from mud.world import (
    FOREST_ELF_BRIARSHADOW_THICKET_KEY,
    FOREST_ELF_LISTENING_POOL_KEY,
    FOREST_ELF_OLD_RIVER_PATH_KEY,
    FOREST_ELF_OUTER_GROVE_KEY,
    FOREST_ELF_START_ROOM_KEY,
    FOREST_ELF_WAYSTONE_BEND_KEY,
    HUMAN_BLACKGLASS_ARCH_KEY,
    HUMAN_CINDER_LANE_KEY,
    HUMAN_LANTERN_COURT_KEY,
    HUMAN_PRACTICE_RING_KEY,
    HUMAN_SOOTSTAIRS_KEY,
    HUMAN_START_ROOM_KEY,
    HUMAN_TRAINING_YARD_KEY,
    HUMAN_VERMIN_PENS_KEY,
    SPOREKIN_FORGOTTEN_GROVE_ROOM_KEY,
    SPOREKIN_MEMORY_PATH_ROOM_KEY,
    SPOREKIN_START_ROOM_KEY,
    SPOREKIN_SURFACE_VERGE_ROOM_KEY,
    SPOREKIN_SURFACEWARD_ROOM_KEY,
)


def X(direction: str, destination: str, name: str, travel: str, **kwargs) -> ExitDefinition:
    return ExitDefinition(
        direction=direction,
        destination_key=destination,
        name=name,
        travel_text=travel,
        **kwargs,
    )


def F(key: str, name: str, *, aliases=(), summary="", examine="", search="", touch="", listen="", condition=None) -> FeatureDefinition:
    return FeatureDefinition(
        key=key,
        name=name,
        aliases=tuple(aliases),
        summary=summary,
        examine_text=examine,
        search_text=search,
        touch_text=touch,
        listen_text=listen,
        condition=condition or ViewCondition(),
    )


def L(key: str, text: str, *, priority=100, condition=None) -> DescriptionLayer:
    return DescriptionLayer(
        key=key,
        text=text,
        priority=priority,
        condition=condition or ViewCondition(),
    )


def complete_room_augmentations() -> dict[str, RoomAugmentation]:
    """Rich scene content for every currently authored room in Astralis."""
    return {
        # ------------------------------------------------------------------
        # HUMAN KINGDOM
        # ------------------------------------------------------------------
        HUMAN_START_ROOM_KEY: RoomAugmentation(
            exit_overrides=(
                X("north", "human_ashen_way", "Ashen Way", "You pass beneath the horned arch and climb into Ashen Way."),
                X(
                    "south", "human_outer_drill_road", "Outer Drill Road",
                    "You leave the gate's shadow and follow the black wall toward the drill road.",
                    door_key="demon_gate_outer_portal",
                    failure_text="The great outer portal is closed; the road beyond is unreachable.",
                ),
            ),
            features=(
                F(
                    "wrought_iron_gates", "Wrought-Iron Gates",
                    aliases=("gate", "gates", "iron gate", "demon gate"),
                    summary="the enormous horn-worked wrought-iron gates",
                    examine="The gates are less defensive ornament than civic declaration: black iron ribs climb overhead into hooked points, while old hammer marks remain visible beneath generations of oil and soot. The imagery is deliberately demonic, not accidental.",
                    search="You find maintenance stamps, old repair welds, and a tiny maker's seal hidden near the lowest hinge. Nothing suggests a secret mechanism.",
                    touch="The iron is cool, slick with protective oil, and faintly rough where age has pitted the surface.",
                ),
                F(
                    "demonic_reliefs", "Demonic Reliefs",
                    aliases=("reliefs", "faces", "carvings", "demonic faces", "horned faces"),
                    summary="the horned stone reliefs worked into the arch",
                    examine="The faces are not depictions of one creature or god. Each is different: stern, beautiful, grotesque, serene. Human masons have spent centuries turning an old insult into heraldry, until 'Demon' became an aesthetic language of its own.",
                    touch="Your fingers trace a polished horn where thousands of other hands have done the same.",
                ),
                F(
                    "cathedral_skyline", "Cathedral Skyline",
                    aliases=("cathedral", "spires", "skyline", "great cathedral"),
                    summary="the distant cathedral spires above the city",
                    examine="Beyond the roofs, the Grand Cathedral dominates the city by design. Flying buttresses and needlelike towers make it look almost skeletal against the sky.",
                    listen="A slow cathedral bell rolls over the rooftops, followed by the thinner answer of smaller bells deeper in the city.",
                ),
                F(
                    "gate_watch", "Gate Watch",
                    aliases=("guards", "watch", "guardhouse", "watchtower", "watchtowers"),
                    summary="the black-uniformed gate watch and iron watchtowers",
                    examine="The gate watch wears dark practical uniforms beneath ceremonial horn-shaped badges. Their attention is on arrivals, wagons, and the road—not on posing for visitors.",
                ),
            ),
            description_layers=(
                L("human_familiarity", "To you, the horns and severe faces do not read as monstrous. They are as ordinary and civic as another kingdom's lions or eagles.", priority=30, condition=ViewCondition(races=("human",))),
                L("outsider_reading", "Seen from outside Human culture, the sheer enthusiasm of the demonic imagery is difficult to mistake: this city chose the name others gave its people and made it monumental.", priority=30, condition=ViewCondition(forbidden_races=("human",))),
                L("night_gate", "Night turns the gate theatrical. Braziers burn beneath the arch, throwing long horn-shaped shadows across the road while the upper watchtowers vanish into darkness.", priority=50, condition=ViewCondition(time_buckets=("night",))),
                L("dusk_gate", "The last daylight catches the cathedral spires while the first gate braziers are being lit, leaving the city briefly divided between violet sky and orange fire.", priority=50, condition=ViewCondition(time_buckets=("dusk",))),
                L("rain_gate", "Rain beads on black iron and turns the cobbles mirror-dark, doubling every torch flame beneath the gate.", priority=60, condition=ViewCondition(weather=("rain",))),
            ),
        ),
        "human_ashen_way": RoomAugmentation(
            exit_overrides=(
                X("south", HUMAN_START_ROOM_KEY, "The Demon Gate", "You descend Ashen Way toward the black arch of the Demon Gate."),
                X("north", "human_cathedral_square", "Cathedral Square", "You climb with the avenue until the street opens beneath the cathedral's shadow."),
                X("west", HUMAN_SOOTSTAIRS_KEY, "The Sootstairs", "You turn from the busy avenue and descend between soot-dark tenements."),
            ),
            features=(
                F("guild_facades", "Guild Facades", aliases=("guilds", "guild offices", "offices"), summary="brass-plated guild offices wedged between shops", examine="Trade-house plaques crowd the doorways: smiths, drovers, chandlers, bookbinders, masons, carriers, and stranger specialties. Status here is expressed through workmanship more often than size.", search="Among the public notices are apprenticeship offers, delivery disputes, fines, and three different warnings about counterfeit seals."),
                F("horned_drainspouts", "Horned Drainspouts", aliases=("drainspouts", "gargoyles", "gutters"), summary="iron drainspouts shaped into grinning horned mouths", examine="Each building seems to have commissioned a different monster. Some are comic, some elegant, and some genuinely unpleasant to stand beneath.", touch="The iron is cold and damp. A drop of old rainwater lands on your wrist with suspicious timing."),
                F("open_taverns", "Open Taverns", aliases=("taverns", "tavern doors", "inns"), summary="warm tavern doors opening onto the avenue", examine="Steam, lamplight, frying onions, and competing music spill from several establishments. None looks quiet; all look accustomed to travelers."),
            ),
            description_layers=(
                L("human_market_read", "You can read the street's hierarchy almost unconsciously: guild colors, shop marks, neighborhood badges, and the subtle difference between respectable black iron and cheap black paint.", priority=30, condition=ViewCondition(races=("human",))),
                L("night_market", "After dark, hanging lamps and tavern windows take over from daylight, and the avenue becomes louder rather than quieter.", priority=50, condition=ViewCondition(time_buckets=("night",))),
                L("rain_market", "Rain runs from every horned gutter at once, forcing pedestrians into awnings and turning the center of the avenue into a shining black channel.", priority=60, condition=ViewCondition(weather=("rain",))),
            ),
        ),
        "human_cathedral_square": RoomAugmentation(
            exit_overrides=(
                X("south", "human_ashen_way", "Ashen Way", "You leave the cathedral's open square and descend into the crowded avenue."),
                X("north", "human_grand_cathedral", "The Grand Cathedral", "You cross the stained light of the square and climb the cathedral steps."),
            ),
            features=(
                F("gargoyle_buttresses", "Gargoyle Buttresses", aliases=("gargoyles", "buttresses", "flying buttresses"), summary="rows of stone gargoyles crouched along the cathedral supports", examine="The gargoyles are part waterspout, part theology, and part civic theater. Their faces range from comic devils to solemn winged judges, each worn pale where rain has run for generations."),
                F("scraped_symbols", "Scraped Symbols", aliases=("symbols", "scratches", "erased symbols", "masonry"), summary="half-erased signs in the square's older masonry", examine="Most have been deliberately scraped until no complete sign remains. Repeated curves and hooked strokes survive where the chisel missed, enough to show that the markings were related rather than random vandalism.", search="Close to the ground, protected by a stone bench, you find one shallow hollow-circle motif that escaped the worst of the scraping."),
                F("stained_glass_light", "Stained-Glass Light", aliases=("stained glass", "colored light", "glass"), summary="bruised red and violet light cast across the paving stones", examine="The windows above depict severe saints, ships crossing black seas, funerary processions, and a blazing star over a walled city. From this angle the images dissolve into color."),
            ),
            description_layers=(
                L("priest_square", "As a Priest, you recognize the square's traffic as partly liturgical: messengers between chapter houses, junior clerics carrying censers, and petitioners waiting for an audience.", priority=30, condition=ViewCondition(classes=("priest",))),
                L("dusk_square", "At dusk the stained glass loses its daylight color one window at a time while lamps kindle around the chapter houses.", priority=50, condition=ViewCondition(time_buckets=("dusk",))),
                L("rain_square", "Rainwater pours from the gargoyles in silver ropes, making the cathedral appear to breathe through a hundred stone mouths.", priority=60, condition=ViewCondition(weather=("rain",))),
            ),
        ),
        "human_grand_cathedral": RoomAugmentation(
            exit_overrides=(X("south", "human_cathedral_square", "Cathedral Square", "You descend the cathedral steps and return to the open square."),),
            features=(
                F("black_pews", "Blackwood Pews", aliases=("pews", "benches", "black pews"), summary="rows of polished blackwood pews", examine="The pew ends are carved with hundreds of tiny names rather than ornament. Some are generations old; some have been cut within the last year.", search="Beneath the nearest seat you find candle wax, a folded scrap of an old hymn, and nothing more secret than ordinary worship."),
                F("stone_saints", "Stone Saints", aliases=("saints", "statues", "stone statues"), summary="severe stone saints surrounded by votive candles", examine="The saints are rendered with unnerving realism: tired eyes, scarred hands, dented armor, patched robes. Holiness here has been sculpted as endurance rather than beauty.", touch="The nearest saint's stone hand is smooth from countless petitioners touching it."),
                F("great_organ", "Great Organ", aliases=("organ", "pipes", "organ loft"), summary="a towering iron-and-wood organ disappearing into the dark", examine="Ranks of blackened pipes climb higher than the candlelight. Decorative iron ribs make the instrument resemble the exposed chest of some impossible beast.", listen="Even at rest the organ murmurs faintly as air moves through the old cathedral."),
            ),
            description_layers=(
                L("priest_nave", "Your training lets you distinguish the clerical ranks at a glance and pick out fragments of familiar liturgy beneath the murmur of the nave.", priority=30, condition=ViewCondition(classes=("priest",))),
                L("undead_cathedral", "No one stops you for being Undead, but several worshippers make the old reflexive sign against death before visibly remembering where they are.", priority=35, condition=ViewCondition(races=("undead",))),
                L("night_nave", "At night the nave becomes almost entirely candlelit; the upper vaults disappear, leaving saints and worshippers floating in islands of red-gold light.", priority=50, condition=ViewCondition(time_buckets=("night",))),
            ),
        ),
        "human_outer_drill_road": RoomAugmentation(
            exit_overrides=(
                X("north", HUMAN_START_ROOM_KEY, "The Demon Gate", "You follow the wall back toward the open Demon Gate."),
                X("west", HUMAN_TRAINING_YARD_KEY, "The Training Yard", "You turn through a low iron gate toward the thud and clang of the training yard."),
            ),
            features=(
                F("black_city_wall", "Black City Wall", aliases=("wall", "city wall", "battlements"), summary="the immense black-stone wall running beside the road", examine="The wall is patched across centuries: different stone, different mortar, different defensive ideas stacked into one continuous boundary.", search="Old mason marks and newer military inspection chalk cover the lower courses."),
                F("watchtowers", "Iron Watchtowers", aliases=("towers", "watchtowers", "tower"), summary="iron-crowned towers overlooking the outer road", examine="Each tower has shutters facing both outward and inward. Whoever designed them intended the watch to observe the road and the city equally."),
                F("drill_tracks", "Drill-Road Tracks", aliases=("tracks", "boot prints", "wagon ruts", "ruts"), summary="overlapping boot prints, wheel ruts, and training traffic", examine="The road records a day's work in mud and dust: marching units, supply carts, dragged practice equipment, and the lighter prints of city runners."),
            ),
            description_layers=(
                L("rain_drill_road", "Rain turns the hard-packed road into slick brown-black mud, and every wagon rut becomes a narrow stream.", priority=60, condition=ViewCondition(weather=("rain",))),
                L("night_drill_road", "At night, braziers on the wall mark the road in measured pools of light while the training yard beyond grows quieter.", priority=50, condition=ViewCondition(time_buckets=("night",))),
            ),
        ),
        HUMAN_TRAINING_YARD_KEY: RoomAugmentation(
            exit_overrides=(
                X("east", "human_outer_drill_road", "Outer Drill Road", "You leave the churned yard through the iron side gate and return to the wall road."),
                X("north", HUMAN_PRACTICE_RING_KEY, "The Practice Ring", "You cross the yard toward the iron-railed practice ring."),
                X("south", HUMAN_VERMIN_PENS_KEY, "The Vermin Pens", "You follow the low stone passage toward the smell and noise of the vermin pens."),
            ),
            features=(
                F("weapon_racks", "Weapon Racks", aliases=("racks", "weapons", "practice weapons"), summary="scarred racks of blunted training weapons", examine="Wooden clubs, dulled blades, weighted staves, and battered shields are sorted by size rather than prestige. Anything truly sharp is conspicuously absent.", search="A chalk tally on the rack tracks broken equipment and names the unfortunate trainee responsible for each piece."),
                F("sand_buckets", "Sand Buckets", aliases=("buckets", "sand", "fire buckets"), summary="rows of sand and water buckets along the fence", examine="They are positioned for fires, blood, and ordinary cleanup in roughly equal measure."),
                F("drill_lines", "Drill Lines", aliases=("fighters", "trainees", "drills", "new fighters"), summary="new fighters repeating footwork beneath veteran supervision", examine="The veterans correct balance more often than strength. Every student who swings too hard eventually gets made to repeat the movement slowly."),
            ),
            description_layers=(
                L("brute_training_eye", "Your Brute training makes the yard's rhythm immediately legible: stance, distance, recovery, then force. The best fighters here waste almost no movement.", priority=30, condition=ViewCondition(classes=("brute",))),
                L("rain_training", "A steady rain does not stop the drills; it simply makes every lesson about footing as well as form.", priority=60, condition=ViewCondition(weather=("rain",))),
            ),
        ),
        HUMAN_PRACTICE_RING_KEY: RoomAugmentation(
            exit_overrides=(X("south", HUMAN_TRAINING_YARD_KEY, "The Training Yard", "You step back through the iron rail into the main training yard."),),
            features=(
                F("training_dummies", "Training Dummies", aliases=("dummies", "dummy", "targets"), summary="battered wooden dummies scarred by generations of practice", examine="The dummies are layered with repairs. Sword grooves, scorch marks, bite-sized chunks, and patched stuffing form an accidental history of beginner mistakes.", search="Several old coins have been hammered into one dummy's base for luck. None comes loose."),
                F("iron_rail", "Iron Ring Rail", aliases=("rail", "railing", "ring"), summary="the waist-high rail surrounding the practice floor", examine="The rail is dented inward in several places where trainees discovered that momentum is difficult to negotiate with."),
            ),
            description_layers=(
                L("night_practice", "Lanterns clipped to the rail make the practice floor look like a small stage after dark.", priority=50, condition=ViewCondition(time_buckets=("night",))),
                L("rain_practice", "Rain darkens the packed dirt and gives the training dummies a miserable, waterlogged appearance.", priority=60, condition=ViewCondition(weather=("rain",))),
            ),
        ),
        HUMAN_VERMIN_PENS_KEY: RoomAugmentation(
            exit_overrides=(X("north", HUMAN_TRAINING_YARD_KEY, "The Training Yard", "You leave the barred pens and climb back toward the open training yard."),),
            features=(
                F("iron_pens", "Iron Pens", aliases=("pens", "bars", "cages", "iron bars"), summary="heavy barred enclosures around the fighting floor", examine="The bars are doubled at the lower edge where rats tend to chew and imps tend to reach. Hinges and latches are maintained with almost obsessive care.", search="Every latch has a second catch positioned out of easy reach from inside."),
                F("catcher_tools", "Catcher Tools", aliases=("tools", "poles", "nets", "catcher gear"), summary="nets, hooked poles, and thick gloves hung on the wall", examine="The equipment is practical and ugly. Several pole handles have been replaced after something chewed through the originals."),
                F("fighting_floor", "Fighting Floor", aliases=("floor", "mud", "arena"), summary="the shallow controlled-combat floor", examine="Old mud, straw, claw marks, and small scorch stains make it obvious that the safety here comes from supervision, not cleanliness."),
            ),
            description_layers=(
                L("night_pens", "At night the pens are lit by shielded lamps that keep the fighting floor bright while leaving the cages around it in shadow.", priority=50, condition=ViewCondition(time_buckets=("night",))),
            ),
        ),
        HUMAN_SOOTSTAIRS_KEY: RoomAugmentation(
            exit_overrides=(
                X("east", "human_ashen_way", "Ashen Way", "You climb out of the cramped stairway and rejoin the brighter traffic of Ashen Way."),
                X("down", HUMAN_CINDER_LANE_KEY, "Cinder Lane", "You descend the soot-black steps until the upper city's noise is trapped above the roofs."),
            ),
            features=(
                F("horned_lintels", "Chipped Horned Lintels", aliases=("lintels", "doorways", "horns"), summary="old demonic stonework above patched Lower-Ward doors", examine="The same civic imagery seen above survives here in cheaper, older forms. Broken horns have been repaired with brick, wood, and occasionally nothing at all."),
                F("iron_lamps", "Old Iron Lamps", aliases=("lamps", "street lamps", "lights"), summary="smoke-stained lamps bolted into the narrow stair walls", examine="Each lamp has been repaired so many times that little of the original metal remains.", search="One lamp bears a tiny scratched arrow pointing downward. It may be a delivery mark, a child's joke, or something more deliberate."),
                F("tenement_windows", "Tenement Windows", aliases=("windows", "tenements", "laundry"), summary="close-set windows and laundry lines above the stairs", examine="Life presses close here: cooking steam, patched curtains, drying clothes, arguments, music, and the occasional face that disappears when noticed."),
            ),
            description_layers=(
                L("human_ward_knowledge", "As a Human, you know this descent marks a social boundary more clearly than any gate: respectable errands happen above, necessary ones often happen below.", priority=30, condition=ViewCondition(races=("human",))),
                L("night_sootstairs", "After dark the stair becomes a vertical chain of weak lamps, with whole landings disappearing between them.", priority=50, condition=ViewCondition(time_buckets=("night",))),
                L("rain_sootstairs", "Rain funnels between the leaning roofs and races down the steps in black rivulets.", priority=60, condition=ViewCondition(weather=("rain",))),
            ),
        ),
        HUMAN_CINDER_LANE_KEY: RoomAugmentation(
            exit_overrides=(
                X("up", HUMAN_SOOTSTAIRS_KEY, "The Sootstairs", "You climb toward the sharper light and busier streets above."),
                X("east", HUMAN_BLACKGLASS_ARCH_KEY, "The Blackglass Arch", "You follow the lane toward the sealed passage beneath smoke-dark glass."),
                X("south", HUMAN_LANTERN_COURT_KEY, "Lantern Court", "You slip through a narrow opening between workshops into the cramped lantern court."),
            ),
            features=(
                F("old_workshops", "Old Workshops", aliases=("workshops", "shops", "brick workshops"), summary="brick-front workshops built against older foundations", examine="Metal filings, dye stains, sawdust, and chemical smells identify trades that no signboard bothers to name. Several foundations descend farther than the visible buildings should require."),
                F("black_gutter", "Black Gutter", aliases=("gutter", "rainwater", "drain"), summary="a narrow gutter carrying dark water along the lane", examine="Coal dust and workshop runoff color the water almost black. Here and there, old dressed stone is visible beneath the newer street.", search="Under a loose grate you glimpse masonry continuing downward into a channel too large to be an ordinary drain."),
                F("guarded_windows", "Guarded Windows", aliases=("windows", "residents", "doorways"), summary="shuttered windows and watchful doorways", examine="People here are not unfriendly so much as practiced at deciding quickly whether a stranger is their problem."),
            ),
            description_layers=(
                L("night_cinder", "At night, workshop light leaks through shutters in thin orange bars while the lane itself stays mostly dark.", priority=50, condition=ViewCondition(time_buckets=("night",))),
                L("rain_cinder", "Rainwater deepens the gutter until it whispers continuously over the buried stonework below.", priority=60, condition=ViewCondition(weather=("rain",))),
            ),
        ),
        HUMAN_BLACKGLASS_ARCH_KEY: RoomAugmentation(
            exit_overrides=(X("west", HUMAN_CINDER_LANE_KEY, "Cinder Lane", "You leave the sealed arch and return to the crooked lane."),),
            features=(
                F("blackglass_arch", "Blackglass Arch", aliases=("arch", "blackglass", "sealed passage"), summary="the smoke-dark arch spanning a passage bricked shut long ago", examine="The glassy stone is not true glass but a dark mineral polished until it reflects distorted shapes. The brickwork sealing the passage is much newer than the arch itself.", search="The mortar varies near the bottom edge. Someone has repaired this wall more recently than the weathering suggests."),
                F("occult_mark", "Hooked Circle Mark", aliases=("mark", "symbol", "occult mark", "hooked circle"), summary="three fresh hooked strokes curling around a hollow circle", examine="Fresh cuts score the soot near the base of the arch. The hand that made them was hurried but deliberate, and someone later tried to scrape the sign away.", touch="The scratches are sharp enough that the newest edges still catch against your fingertip."),
                F("old_masonry", "Ancient Masonry", aliases=("masonry", "stones", "wall"), summary="weathered stone predating the surrounding Lower Wards", examine="The blocks are larger and more precisely fitted than the later brickwork. Whatever stood here originally was important enough to build for centuries."),
            ),
            description_layers=(
                L("night_blackglass", "At night the arch reflects almost nothing, becoming a darker rectangle inside the darkness of the lane.", priority=50, condition=ViewCondition(time_buckets=("night",))),
                L("rain_blackglass", "Rain makes the arch shine like wet obsidian and pools in the fresh cuts of the hooked-circle mark.", priority=60, condition=ViewCondition(weather=("rain",))),
            ),
        ),
        HUMAN_LANTERN_COURT_KEY: RoomAugmentation(
            exit_overrides=(X("north", HUMAN_CINDER_LANE_KEY, "Cinder Lane", "You leave the red lantern behind and return to Cinder Lane."),),
            features=(
                F("red_lantern", "Red Lantern", aliases=("lantern", "red light"), summary="the single red lantern that burns even in daylight", examine="The lantern is enclosed in old red glass and fed by a surprisingly clean oil reservoir. Someone maintains it carefully.", search="A tiny maker's stamp on the frame is too worn to read, but the wick has been trimmed recently."),
                F("dry_cistern", "Dry Cistern", aliases=("cistern", "fountain", "dead fountain", "well"), summary="a public cistern whose basin has long since gone dry", examine="The stone basin is cracked and dusty. Its central throat has been capped with an iron plate whose bolts are newer than the rest of the court.", search="Air moves faintly through the seam beneath the iron cap. Whatever is below is not completely sealed."),
                F("balcony_web", "Balcony Web", aliases=("balconies", "fire escapes", "stairs"), summary="a maze of balconies and iron stairs overhead", examine="The court has accumulated vertical shortcuts over generations. Residents can cross three buildings without touching street level."),
            ),
            description_layers=(
                L("night_lantern", "After dark the red lantern stains the dry cistern and lower balconies the color of old blood.", priority=50, condition=ViewCondition(time_buckets=("night",))),
                L("rain_lantern", "Rain drums on the iron fire escapes but never fills the capped cistern below.", priority=60, condition=ViewCondition(weather=("rain",))),
            ),
        ),

        # ------------------------------------------------------------------
        # FOREST ELVES
        # ------------------------------------------------------------------
        FOREST_ELF_START_ROOM_KEY: RoomAugmentation(
            exit_overrides=(X("north", "forest_elf_greenway", "The Greenway", "You leave the seven stones behind and follow the soft path beneath the trees."),),
            features=(
                F("circle_stones", "Seven Circle Stones", aliases=("stones", "circle", "druid stones"), summary="seven weathered stones marking the Druidic Circle's meeting place", examine="Each stone bears generations of shallow hand-carved marks: leaves, moons, animal tracks, names, seasons, and tiny private symbols whose meanings have been lost.", touch="The stone is warm where sunlight reaches it and cool beneath the moss."),
                F("living_homes", "Living-Trunk Homes", aliases=("homes", "houses", "tree homes", "buildings"), summary="timber homes shaped around living trees", examine="The builders avoided cutting major limbs. Walls bend, roofs notch around trunks, and repairs have been made with the expectation that the trees will keep growing."),
                F("fern_gardens", "Fern Gardens", aliases=("gardens", "ferns", "herbs"), summary="quiet household gardens beneath the canopy", examine="Herbs, edible shoots, medicinal mosses, and flowers grow in careful layers suited to broken forest light."),
            ),
            description_layers=(
                L("forest_elf_home", "Every path, stone, and roofline carries the unconscious familiarity of home; you know which paths are public without needing signs.", priority=30, condition=ViewCondition(races=("forest_elf",))),
                L("outsider_elf_town", "To an outsider the settlement can seem almost hidden despite being all around you; buildings yield visually to trunks, gardens, and canopy.", priority=30, condition=ViewCondition(forbidden_races=("forest_elf",))),
                L("night_circle", "At night, hooded lamps and pale flowers define the clearing without overwhelming the darkness beyond it.", priority=50, condition=ViewCondition(time_buckets=("night",))),
                L("rain_circle", "Rain whispers across leaves high overhead, reaching the clearing mostly as large delayed drops shaken loose from the canopy.", priority=60, condition=ViewCondition(weather=("rain",))),
            ),
        ),
        "forest_elf_greenway": RoomAugmentation(
            exit_overrides=(
                X("south", FOREST_ELF_START_ROOM_KEY, "Circle Clearing", "You follow the broad path back toward the seven stones and clustered homes."),
                X("east", FOREST_ELF_OLD_RIVER_PATH_KEY, "The Old River Path", "You turn toward the sound of running water and let the Greenway narrow around you."),
            ),
            features=(
                F("leaf_markers", "Carved Leaf Markers", aliases=("markers", "signs", "carvings", "leaf signs"), summary="small carved markers indicating paths through the town edge", examine="The symbols favor destinations over directions: a cup for the gathering hall, three seeds for the gardens, a fish-line for the river path."),
                F("silver_birches", "Silver-Barked Birches", aliases=("birches", "trees", "silver trees"), summary="slender birches shining between older beeches", examine="Their bark peels in thin pale curls. Small offerings of thread and dried flowers have been tied to two of the lower branches."),
                F("townside_paths", "Townside Paths", aliases=("side paths", "paths", "trails"), summary="narrow footpaths slipping toward homes and gardens", examine="None needs a formal sign to locals. Their wear, plantings, and small household markers make their purposes obvious to anyone raised here."),
            ),
            description_layers=(
                L("forest_elf_path_sense", "You read the small path markers almost without looking; the forest town communicates in habit and symbol more often than posted words.", priority=30, condition=ViewCondition(races=("forest_elf",))),
                L("night_greenway", "Moonlight catches the birch trunks in broken silver bands while the side paths disappear into deeper shadow.", priority=50, condition=ViewCondition(time_buckets=("night",))),
                L("rain_greenway", "Wet fern fronds lean into the path, and the carved markers darken until their cuts stand out sharply.", priority=60, condition=ViewCondition(weather=("rain",))),
            ),
        ),
        FOREST_ELF_OLD_RIVER_PATH_KEY: RoomAugmentation(
            exit_overrides=(
                X("west", "forest_elf_greenway", "The Greenway", "You leave the river and follow the broader path back toward the forest town."),
                X("north", FOREST_ELF_WAYSTONE_BEND_KEY, "Waystone Bend", "You follow the river upstream toward the cedar and leaning waystone."),
            ),
            features=(
                F("clear_river", "Clear River", aliases=("river", "water", "stream"), summary="cold clear water sliding over flat brown stones", examine="Minnows hold themselves almost motionless in the current. The water is clear enough to show every pebble until the channel deepens under roots.", touch="The water is cold enough to make your fingers ache after only a moment.", listen="The river speaks mostly in small sounds: current against roots, water over stone, an occasional hollow knock from submerged wood."),
                F("white_flowers", "White River Flowers", aliases=("flowers", "white flowers", "plants"), summary="tiny white blooms in the sunlit gaps beside the path", examine="The flowers close when shaded and reopen quickly in sunlight, making scattered patches seem to blink as branches move overhead."),
                F("moss_steps", "Moss-Covered Root Steps", aliases=("roots", "steps", "moss"), summary="old roots forming natural steps along the riverbank", examine="Generations of careful feet have worn shallow smooth places into the roots without cutting them back."),
            ),
            description_layers=(
                L("druid_river", "As a Druid, you notice how deliberately little the path interferes with the riverbank; the route yields to roots and seasonal water rather than forcing them aside.", priority=30, condition=ViewCondition(classes=("druid",))),
                L("rain_river", "Rain roughens the river's glassy surface and fills the air with the scent of moss and newly exposed soil.", priority=60, condition=ViewCondition(weather=("rain",))),
            ),
        ),
        FOREST_ELF_WAYSTONE_BEND_KEY: RoomAugmentation(
            exit_overrides=(
                X("south", FOREST_ELF_OLD_RIVER_PATH_KEY, "The Old River Path", "You follow the river back downstream along the old path."),
                X("east", FOREST_ELF_LISTENING_POOL_KEY, "The Listening Pool", "You pass through the willow curtains toward the widening, quieter water."),
            ),
            features=(
                F("old_waystone", "Old Waystone", aliases=("waystone", "stone marker", "marker", "stone"), summary="a moss-softened stone bearing the leaf-and-circle emblem", examine="Moss fills most of the carving, but the surviving shallow lines form a practical sequence: a river bend, a still pool, and a single oak at the edge of thick woods.", search="At the back of the stone, nearly at ground level, generations of travelers have scratched tiny initials and seasonal marks."),
                F("ancient_cedar", "Ancient Cedar", aliases=("cedar", "tree", "old cedar"), summary="a great cedar sheltering the bend and waystone", examine="The cedar's lower branches have been carefully lifted away from the path over decades rather than cut all at once. Its trunk is broad enough to hide several people."),
                F("willow_curtains", "Willow Curtains", aliases=("willows", "willow branches", "curtains"), summary="long willow branches veiling the eastern path", examine="The branches brush the river and path alike, making the route east look more private than hidden."),
            ),
            description_layers=(
                L("forest_elf_waystone_memory", "The emblem is familiar from childhood wayfinding: not sacred exactly, but old enough that practical instruction and tradition have become difficult to separate.", priority=30, condition=ViewCondition(races=("forest_elf",))),
                L("rain_waystone", "Rain makes the cedar fragrant and turns the waystone's moss almost luminous green.", priority=60, condition=ViewCondition(weather=("rain",))),
            ),
        ),
        FOREST_ELF_LISTENING_POOL_KEY: RoomAugmentation(
            exit_overrides=(
                X("west", FOREST_ELF_WAYSTONE_BEND_KEY, "Waystone Bend", "You leave the still pool and return through the willow curtains to the waystone."),
                X("north", FOREST_ELF_OUTER_GROVE_KEY, "The Outer Grove", "You follow the narrowing trail north as the tended woodland begins to fall away."),
            ),
            features=(
                F("listening_pool", "Listening Pool", aliases=("pool", "water", "still water"), summary="a glassy widening of the river beneath willows", examine="The pool is not perfectly still; tiny currents bend reflections in slow patterns that are difficult to notice until you stop moving.", touch="The surface breaks around your fingers, sending rings outward beneath the willow reflections.", listen="Beneath birdsong and the faint slide of water is a second rhythm—subtle enough to be current, root, insect, or magic."),
                F("low_stone_shelf", "Low Stone Shelf", aliases=("shelf", "stone", "rock ledge"), summary="a dark shelf of stone just beneath the waterline", examine="Water sheets across the stone so evenly that it barely splashes. Pale mineral lines show where the river sits in drier seasons."),
                F("dragonflies", "Dragonflies", aliases=("flies", "insects"), summary="bright dragonflies hovering above the pool", examine="They repeatedly return to the same invisible positions over the water, as if each owns a tiny piece of air."),
            ),
            description_layers=(
                L("forest_elf_listening", "The stillness here is culturally familiar to you: places like this are not treated as shrines, but everyone knows to lower their voice near them.", priority=30, condition=ViewCondition(races=("forest_elf",))),
                L("night_pool", "At night the pool becomes a black mirror broken by moonlight, insects, and the occasional pale flicker beneath the surface.", priority=50, condition=ViewCondition(time_buckets=("night",))),
                L("rain_pool", "Rain erases the pool's stillness, covering it in thousands of overlapping rings without quite destroying the underlying hush.", priority=60, condition=ViewCondition(weather=("rain",))),
            ),
        ),
        FOREST_ELF_OUTER_GROVE_KEY: RoomAugmentation(
            exit_overrides=(
                X("south", FOREST_ELF_LISTENING_POOL_KEY, "The Listening Pool", "You retreat toward the quieter water and the tended paths beyond."),
                X("north", FOREST_ELF_BRIARSHADOW_THICKET_KEY, "Briarshadow Thicket", "You pass the boundary oak and push beneath the darker wall of thorn."),
            ),
            features=(
                F("boundary_oak", "Boundary Oak", aliases=("oak", "boundary tree", "tree"), summary="the old oak marking the edge of tended forest", examine="Three deep claw marks scar the trunk above shoulder height. Newer red cloth has been tied beneath them where no traveler could miss it.", touch="The bark is deeply ridged. The claw grooves are old and weather-rounded, but still broad enough to fit several fingers."),
                F("red_warning_cloth", "Red Warning Cloth", aliases=("cloth", "red cloth", "warning"), summary="a fresh strip of red cloth tied beneath old claw marks", examine="The cloth is ordinary, replaced recently, and intentionally bright. The Circle apparently prefers warnings that cannot be mistaken for poetry."),
                F("strange_tracks", "Unfamiliar Tracks", aliases=("tracks", "prints", "animal tracks"), summary="tracks crossing the ground beyond the maintained path", examine="Several are deer and boar. Others overlap too badly to identify, though at least one print is broader than you would expect from anything wandering this close to town."),
            ),
            description_layers=(
                L("forest_elf_boundary", "You were taught what the red cloth means long before you were old enough to travel alone: beyond this oak, the forest is no longer managed for your safety.", priority=30, condition=ViewCondition(races=("forest_elf",))),
                L("night_outer_grove", "After dark the warning cloth loses its color and the thicket beyond becomes a single wall of black branches.", priority=50, condition=ViewCondition(time_buckets=("night",))),
                L("rain_outer_grove", "Rain brings out the tracks in the soft ground with uncomfortable clarity.", priority=60, condition=ViewCondition(weather=("rain",))),
            ),
        ),
        FOREST_ELF_BRIARSHADOW_THICKET_KEY: RoomAugmentation(
            exit_overrides=(X("south", FOREST_ELF_OUTER_GROVE_KEY, "The Outer Grove", "You force your way back through the briars toward the boundary oak."),),
            features=(
                F("broad_tracks", "Broad Fresh Tracks", aliases=("tracks", "prints", "broad tracks"), summary="large fresh tracks pressed into damp earth", examine="The impressions are broad, deep, and partially smeared by leaf litter. Whatever made them carries substantial weight and moved through here recently.", search="Following the clearest impressions for only a few steps reveals bark scraped from a trunk at roughly chest height."),
                F("snapped_saplings", "Snapped Saplings", aliases=("saplings", "broken trees", "branches"), summary="young trees broken well above the height of a deer", examine="The breaks are ragged rather than cut. Several stems bend in the same direction, marking where something large forced itself through."),
                F("torn_warning_cloth", "Torn Warning Cloth", aliases=("cloth", "red cloth", "warning cloth"), summary="half a red warning strip caught in blackthorn", examine="The missing half was not untied. The fabric has been stretched and ripped, leaving threads caught on multiple thorns."),
                F("blackthorn_wall", "Blackthorn Wall", aliases=("briars", "thorns", "blackthorn", "thicket"), summary="dense thorny growth hemming in the trail", examine="The thorns knit together so densely that leaving the trail would mean forcing through them one painful step at a time."),
            ),
            description_layers=(
                L("forest_elf_danger_sense", "The absence of familiar leaf-markers is more unsettling than any warning sign. No one from the town intends this stretch to feel domesticated.", priority=30, condition=ViewCondition(races=("forest_elf",))),
                L("night_briarshadow", "At night the canopy closes completely. Anything beyond a few paces exists only as sound, smell, and movement in the leaves.", priority=50, condition=ViewCondition(time_buckets=("night",))),
                L("rain_briarshadow", "Rain slicks every thorn and deepens the fresh tracks until they hold dark water.", priority=60, condition=ViewCondition(weather=("rain",))),
            ),
        ),

        # ------------------------------------------------------------------
        # SPOREKIN
        # ------------------------------------------------------------------
        SPOREKIN_START_ROOM_KEY: RoomAugmentation(
            exit_overrides=(X("north", "sporekin_mycelial_gallery", "The Mycelial Gallery", "You follow the living threads north between curtains of mycelium."),),
            features=(
                F("luminous_shelves", "Luminous Fungal Shelves", aliases=("fungi", "mushrooms", "shelves", "glowing caps"), summary="broad blue-green fungi lighting the cavern", examine="The largest shelves glow from thin branching veins beneath translucent flesh. Smaller growths cluster in their shadow, sharing the same faint color.", touch="The fungal surface is cool, firm, and slightly springy beneath your fingers."),
                F("pale_roots", "Pale Rootwork", aliases=("roots", "rootwork", "pale roots"), summary="pale roots threading through the cavern stone", examine="The roots vanish into cracks too narrow to follow. Fine mycelial threads wrap several of them without choking their growth."),
                F("water_beads", "Stone Water-Beads", aliases=("water", "droplets", "beads"), summary="slow droplets forming along the cavern wall", examine="Each droplet gathers for a long time before falling into dark soil with a sound barely louder than breath.", listen="Drips answer one another across the hollow at irregular intervals."),
            ),
            description_layers=(
                L("sporekin_collective_home", "The living network beneath you is not background sensation. It is presence: countless distant impressions touching the edge of your mind without demanding attention.", priority=30, condition=ViewCondition(races=("sporekin",))),
                L("outsider_underways", "If you are not Sporekin, the quiet is stranger: there are signs of habitation everywhere, yet almost no voices and few obvious boundaries between settlement and ecology.", priority=30, condition=ViewCondition(forbidden_races=("sporekin",))),
            ),
        ),
        "sporekin_mycelial_gallery": RoomAugmentation(
            exit_overrides=(
                X("south", SPOREKIN_START_ROOM_KEY, "Lumen Hollow", "You follow the branching mycelium back toward the blue-green hollow."),
                X("east", "sporekin_rootwell_ascent", "Rootwell Ascent", "You follow cooler air east toward the root-choked rising tunnel."),
            ),
            features=(
                F("living_network", "Living Mycelial Network", aliases=("mycelium", "threads", "network", "white threads"), summary="branching white mycelium webbing the floor and walls", examine="The threads vary from hair-fine strands to cords thick as fingers. They cross, divide, merge, and vanish beneath the soil in patterns too complex to be decorative.", touch="A faint tingling travels through your fingertips and is gone before you can decide whether it was sensation or thought."),
                F("low_star_caps", "Low-Star Caps", aliases=("caps", "mushrooms", "stars", "glowing mushrooms"), summary="small bioluminescent caps scattered through the gallery", examine="Their light is dim individually, but together they turn the gallery floor into something resembling a night sky laid flat beneath your feet."),
                F("root_tunnel", "Root-Choked Tunnel", aliases=("tunnel", "east tunnel", "roots"), summary="the rising eastern passage where cooler air moves", examine="Roots narrow the passage without sealing it. Polished patches show where generations of bodies have passed between them."),
            ),
            description_layers=(
                L("sporekin_network_voice", "Here the shared consciousness feels wider. Thoughts do not arrive as sentences so much as direction, recognition, memory, and the reassuring fact of others nearby.", priority=30, condition=ViewCondition(races=("sporekin",))),
            ),
        ),
        "sporekin_rootwell_ascent": RoomAugmentation(
            exit_overrides=(
                X("west", "sporekin_mycelial_gallery", "The Mycelial Gallery", "You descend from the roots into the wider mycelial gallery."),
                X("up", SPOREKIN_SURFACEWARD_ROOM_KEY, "The Veiled Grotto", "You climb the great roots toward cooler air and the pale suggestion of daylight."),
            ),
            features=(
                F("great_roots", "Great Root Handholds", aliases=("roots", "handholds", "root ladder"), summary="massive roots forming a natural climb through the shaft", examine="The roots have grown into an accidental ladder. Smooth areas show the routes most often taken; fine new roots slowly reclaim less-used ledges.", touch="The root is firm and faintly damp, with a living give beneath the bark."),
                F("amber_mushrooms", "Amber Mushrooms", aliases=("amber caps", "mushrooms", "caps"), summary="warm amber fungi clustered along the ascent", examine="Their color is warmer than the blue-green growths below, and their glow intensifies slightly where cooler air moves across them."),
                F("surface_air", "Cool Surface Air", aliases=("air", "breeze", "draft"), summary="a faint cool draft descending from above", examine="The moving air carries scents absent below: wet leaves, open water, and something sharp and green.", listen="Far above, irregular droplets strike roots and stone with the loose rhythm of rainfall."),
            ),
            description_layers=(
                L("sporekin_upward_pull", "Through the shared network comes a faint directional pressure—not command exactly, but collective attention leaning upward with you.", priority=30, condition=ViewCondition(races=("sporekin",))),
            ),
        ),
        SPOREKIN_SURFACEWARD_ROOM_KEY: RoomAugmentation(
            exit_overrides=(
                X("down", "sporekin_rootwell_ascent", "Rootwell Ascent", "You slip back beneath the root veil and descend toward the warmer Underways."),
                X("north", SPOREKIN_SURFACE_VERGE_ROOM_KEY, "Rainroot Verge", "You part the living root veil and step into the breathing surface world."),
            ),
            features=(
                F("root_veil", "Living Root Veil", aliases=("veil", "roots", "root curtain", "entrance"), summary="a woven screen of roots, moss, and stone hiding the surface opening", examine="From inside, the route is obvious. From outside, overlapping root, moss, and stone would make the entrance look like an ordinary bank.", touch="Fine roots flex apart under careful pressure and settle back when released."),
                F("filtered_daylight", "Filtered Daylight", aliases=("daylight", "light", "sunlight"), summary="pale surface light filtering through hairline openings", examine="After the fungal glow below, natural daylight seems colorless at first. Gradually it resolves into silver, green, brown, and the muted white of the sky."),
                F("edge_fungi", "Edge Fungi", aliases=("fungi", "mushrooms", "luminous mushrooms"), summary="small luminous mushrooms surviving near the surface boundary", examine="These caps glow more faintly than their deeper relatives and angle themselves away from the brightest openings."),
            ),
            description_layers=(
                L("sporekin_veil_meaning", "You feel the cultural weight of the veil more than you see it: not a border against the surface, but a reminder that most of your people choose to remain unseen.", priority=30, condition=ViewCondition(races=("sporekin",))),
                L("rain_grotto", "Rainwater threads through the root ceiling in fine silver lines, feeding shallow channels cut into the stone floor.", priority=60, condition=ViewCondition(weather=("rain",))),
            ),
        ),
        SPOREKIN_SURFACE_VERGE_ROOM_KEY: RoomAugmentation(
            exit_overrides=(
                X("south", SPOREKIN_SURFACEWARD_ROOM_KEY, "The Veiled Grotto", "You find the almost invisible root opening and slip back beneath the surface."),
                X("east", SPOREKIN_FORGOTTEN_GROVE_ROOM_KEY, "The Forgotten Grove", "You follow the faint blue-green pulse east beneath the bent old tree."),
            ),
            features=(
                F("hidden_underway_entrance", "Hidden Underway Entrance", aliases=("entrance", "root entrance", "underways", "mossy opening"), summary="the nearly invisible entrance back beneath the roots", examine="Viewed from the surface, the route is astonishingly easy to miss. Moss, stone, root, and shadow align to make an opening disappear in plain sight.", search="Once you know where to look, polished root surfaces and faint disturbed soil reveal regular passage."),
                F("bent_old_tree", "Bent Old Tree", aliases=("tree", "bent tree", "old tree"), summary="an ancient tree leaning east over the wet ground", examine="The trunk bent long ago and kept growing. Several roots rise above the soil like ribs, pointing roughly toward the distant fungal pulse."),
                F("surface_rain", "Surface Rain", aliases=("rain", "mist", "water"), summary="rain and mist moving through the open forest", examine="Without a cavern ceiling, water comes from everywhere at once: leaf tips, bark, mist, sky, and shaken branches.", listen="The surface is almost overwhelmingly loud after the Underways—rain, insects, distant birds, moving leaves, and water striking water."),
            ),
            description_layers=(
                L("sporekin_surface_senses", "The open sky feels less like empty space than an absence of shelter. The shared consciousness is still present, but thinner here, stretched beneath unfamiliar noise.", priority=30, condition=ViewCondition(races=("sporekin",))),
                L("night_verge", "At night the concealed Underway entrance becomes nearly impossible to distinguish even when you know exactly where it is.", priority=50, condition=ViewCondition(time_buckets=("night",))),
                L("rain_verge", "Rain intensifies until every broad leaf sheds water in steady streams and the blue-green pulse east becomes easier to see against the gray forest.", priority=60, condition=ViewCondition(weather=("rain",))),
            ),
        ),
        SPOREKIN_FORGOTTEN_GROVE_ROOM_KEY: RoomAugmentation(
            exit_overrides=(X("west", SPOREKIN_SURFACE_VERGE_ROOM_KEY, "Rainroot Verge", "You leave the old mushroom ring and follow the wet roots back toward the verge."),),
            extra_exits=(
                X(
                    "north", SPOREKIN_MEMORY_PATH_ROOM_KEY, "The Memory Path",
                    "You follow the spore-sigil north onto the newly remembered path.",
                    condition=ViewCondition(required_flags=("sporekin_forgotten_pulse_solved",)),
                    hidden_when_unavailable=True,
                ),
            ),
            features=(
                F("mushroom_ring", "Four-Mushroom Ring", aliases=("mushrooms", "mushroom ring", "ring", "caps"), summary="four luminous caps: blue, amber, violet, and ivory", examine="The four caps form a deliberate circle around the old black stone. Their colors answer different traces of spore residue in the shallow channels below.", listen="The shared consciousness is distant here. Beneath the rain is only an old four-beat memory: cool blue, warm amber, dusk violet, pale ivory."),
                F("black_memory_stone", "Black Memory Stone", aliases=("stone", "black stone", "memory stone"), summary="a flat black stone half-swallowed by moss", examine="Shallow channels link four spore-stained hollows around the stone. The oldest residue traces a path from blue to amber, then violet, then ivory.", touch="The stone is unexpectedly warm beneath the moss, as though it has been holding a small amount of heat for a very long time."),
                F("mycelial_scars", "Mycelial Scars", aliases=("scars", "threads", "mycelium"), summary="thin pale scars radiating outward through the soil", examine="Most of the network here is dead or dormant. A few threads still catch the fungal light, but they do not carry the dense living presence of the Underways."),
            ),
            description_layers=(
                L("sporekin_faded_memory", "To a Sporekin, the grove feels like reaching for a familiar thought and finding only its shape. Something here belonged to the collective once and has nearly fallen out of memory.", priority=30, condition=ViewCondition(races=("sporekin",))),
                L("remembered_path", "A faint spore-shaped sigil hangs above the roots, pointing north toward a path that was invisible before the old pulse was restored.", priority=70, condition=ViewCondition(required_flags=("sporekin_forgotten_pulse_solved",))),
                L("night_forgotten", "At night the four caps become the grove's only clear landmarks, their colors floating above black soil and roots.", priority=50, condition=ViewCondition(time_buckets=("night",))),
                L("rain_forgotten", "Rain gathers on each luminous cap until colored droplets fall into the black stone's shallow channels.", priority=60, condition=ViewCondition(weather=("rain",))),
            ),
        ),
        SPOREKIN_MEMORY_PATH_ROOM_KEY: RoomAugmentation(
            exit_overrides=(X("south", SPOREKIN_FORGOTTEN_GROVE_ROOM_KEY, "The Forgotten Grove", "You follow the fading fungal flecks south toward the restored mushroom ring."),),
            features=(
                F("fungal_waylights", "Fading Fungal Waylights", aliases=("lights", "flecks", "fungal light", "glowing stones"), summary="small flecks of fungal light marking the old trail", examine="The growths are sparse but patterned, each appearing just before the previous one would leave sight. They feel less like decoration than an old navigational convention."),
                F("old_root_arches", "Old Root Arches", aliases=("roots", "arches", "root arches"), summary="great roots crossing above the narrow path", examine="Several roots bear pale scars where mycelium once ran much more thickly. The route appears to have been connected to a larger living network long ago."),
                F("unexplored_north", "Unexplored North", aliases=("north", "ahead", "trail ahead"), summary="the unfinished continuation of the old path", examine="The path clearly continues beyond the currently authored world. Fungal flecks vanish between roots ahead, promising a deeper Sporekin history still waiting to be built."),
            ),
            description_layers=(
                L("sporekin_memory_path", "The path carries a faint emotional texture through the shared consciousness: recognition without context, like remembering a place from a life you did not personally live.", priority=30, condition=ViewCondition(races=("sporekin",))),
                L("night_memory_path", "At night the fungal waylights become a clean chain of tiny stars beneath the root arches.", priority=50, condition=ViewCondition(time_buckets=("night",))),
                L("rain_memory_path", "Rain runs down the old roots and briefly brightens every fungal fleck it touches.", priority=60, condition=ViewCondition(weather=("rain",))),
            ),
        ),
    }
