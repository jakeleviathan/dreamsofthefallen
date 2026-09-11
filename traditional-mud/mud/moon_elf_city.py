from __future__ import annotations

from dataclasses import replace

import mud.character_options as character_options
import mud.world as legacy_world
from mud.room_engine import (
    DescriptionLayer,
    ExitDefinition,
    FeatureDefinition,
    RoomAugmentation,
    ViewCondition,
)
from mud.world import NpcDefinition, RoomDefinition


MOON_ELF_REGION_KEY = "moon_peaks"
MOON_ELF_CITY_NAME = "High Horizon"

MOON_ELF_START_ROOM_KEY = "moon_elf_high_horizon_plaza"
MOON_ELF_SKYCOURT_KEY = "moon_elf_skycourt"
MOON_ELF_JOURNAL_GALLERY_KEY = "moon_elf_journal_gallery"
MOON_ELF_MOONMIRROR_WALK_KEY = "moon_elf_moonmirror_walk"
MOON_ELF_NIGHT_MARKET_KEY = "moon_elf_night_market"
MOON_ELF_WIND_TERRACE_KEY = "moon_elf_wind_terrace"
MOON_ELF_SPIRE_LOBBY_KEY = "moon_elf_skyglass_spire_lobby"
MOON_ELF_HORIZON_DECK_KEY = "moon_elf_horizon_deck"
MOON_ELF_PENTHOUSE_KEY = "moon_elf_high_aerie_penthouse"

MOON_ELF_CITY_ROOM_KEYS = (
    MOON_ELF_START_ROOM_KEY,
    MOON_ELF_SKYCOURT_KEY,
    MOON_ELF_JOURNAL_GALLERY_KEY,
    MOON_ELF_MOONMIRROR_WALK_KEY,
    MOON_ELF_NIGHT_MARKET_KEY,
    MOON_ELF_WIND_TERRACE_KEY,
    MOON_ELF_SPIRE_LOBBY_KEY,
    MOON_ELF_HORIZON_DECK_KEY,
    MOON_ELF_PENTHOUSE_KEY,
)

MOON_ELF_CITY_INTRO_FLAG = "moon_elf_high_horizon_introduced"
MOON_ELF_PENTHOUSE_ACCESS_FLAG = "moon_elf_high_aerie_access"


GOVERNMENT_LINES: tuple[str, ...] = (
    "High Horizon is governed by the Horizon Council, a small rotating council of civic stewards rather than a monarch or hereditary ruling house.",
    "Council seats turn over on staggered civic terms. The schedule is administrative, not an omen read from the moon, and no seat belongs permanently to a family.",
    "Before a major vote, the strongest advocate for a proposal must present a Counterview: the strongest serious case against the position they currently favor.",
    "Major decisions are recorded with the evidence considered, the dissenting arguments, and the conditions that would justify reopening the decision later.",
    "Changing one's mind in public after the facts change is treated as responsible government rather than humiliation. Refusing to reconsider merely to look consistent is not admired.",
    "The Horizon Council is a civic institution, not a priesthood. The Moon Elf religious tradition and its eventual deity or deities remain separate questions.",
)

CITY_LINES: tuple[str, ...] = (
    "High Horizon occupies a broad mountain ridge in the Moon Peaks, where pale stone streets, narrow bridges, terraced homes, and open plazas preserve long views of the sky and surrounding ranges.",
    "The city is calm without being sleepy. By night, tea rooms, small markets, musicians, observatories, journal houses, and public terraces remain active beneath shielded lamps and moonlight.",
    "Mirror frames, weather chimes, horizon rails, and viewing platforms are ordinary civic furniture. They reflect a culture that likes to compare what can be seen from more than one angle.",
    "The tallest landmark is Skyglass Spire, a true vertical city tower: part observatory, part residence, part public lookout, and unmistakably a fantasy skyscraper rising above the ridge.",
)

SPIRE_LINES: tuple[str, ...] = (
    "Skyglass Spire rises dozens of stories above High Horizon in pale structural ribs, dark skyglass, stacked balconies, hanging gardens, residences, observatory floors, and public viewing decks.",
    "It is intentionally a fantasy skyscraper translated into Moon Elf architecture rather than a modern glass office block. Its height serves the same civic love of long horizons that shaped the rest of the city.",
    "The public route reaches the Horizon Deck near the crown. Above it is the High Aerie Penthouse, a private suite and observatory residence reserved for future personal ownership rather than ordinary starter access.",
)

PENTHOUSE_LINES: tuple[str, ...] = (
    "The High Aerie Penthouse crowns Skyglass Spire above the public Horizon Deck.",
    "It is a genuine private penthouse suite: a moonward salon, sleeping chambers, a private observatory, a sheltered rooftop garden, broad windows, and balconies looking over the entire Moon Peaks.",
    "The suite already exists in the world, but its private ascent remains locked until the character who owns it is granted access. It is meant to become a real home, not merely scenery.",
)


MOON_ELF_ROOMS: tuple[RoomDefinition, ...] = (
    RoomDefinition(
        key=MOON_ELF_START_ROOM_KEY,
        name="High Horizon Plaza",
        region_key=MOON_ELF_REGION_KEY,
        description=(
            "The Moon Peaks open around a broad plaza laid across the crown of a high ridge. Pale stone underfoot is broken by strips of dark slate that point toward distant summits rather than toward any monument at the center. Low windbreak walls preserve the view while making the plaza comfortable enough for benches, tea tables, and evening conversation. "
            "To the north, shallow steps rise to the public Skycourt. A journal arcade lies west, a night market east, and higher terraces climb above the plaza. Far beyond the roofs, Skyglass Spire stands so tall and slender that its upper windows catch light long after the lower city falls into shadow."
        ),
        exits={
            "north": MOON_ELF_SKYCOURT_KEY,
            "west": MOON_ELF_JOURNAL_GALLERY_KEY,
            "east": MOON_ELF_NIGHT_MARKET_KEY,
            "up": MOON_ELF_WIND_TERRACE_KEY,
        },
        tags=("moon_elf_start", "safe", "city", "high_altitude", "open_horizon", "pleasant"),
    ),
    RoomDefinition(
        key=MOON_ELF_SKYCOURT_KEY,
        name="The Skycourt",
        region_key=MOON_ELF_REGION_KEY,
        description=(
            "An open civic court occupies a sheltered notch in the ridge, roofed only around its edges. Curved benches face a low speaking floor rather than a raised throne. Behind it, a long wall carries the current Horizon Council roster, upcoming term rotations, public petitions, and decisions scheduled for review. "
            "The room makes government visible without making it grandiose. People come and go with journals under their arms, listening from the edge before deciding whether they have anything useful to add."
        ),
        exits={"south": MOON_ELF_START_ROOM_KEY, "east": MOON_ELF_MOONMIRROR_WALK_KEY},
        npc_keys=("moon_elf_horizon_steward",),
        tags=("safe", "government", "public_forum", "horizon_council", "counterview"),
    ),
    RoomDefinition(
        key=MOON_ELF_JOURNAL_GALLERY_KEY,
        name="Journal Gallery",
        region_key=MOON_ELF_REGION_KEY,
        description=(
            "A long, warm gallery is lined with family cabinets, copying desks, reading alcoves, and narrow windows that frame different parts of the valley. Some shelves hold generations of private journals; others contain volumes families chose to make public after the writers died. "
            "Corrections are not hidden. Colored ribbons and marginal notes visibly connect an old conclusion to the later page where someone reconsidered it. The atmosphere is closer to a neighborhood library than a sacred archive."
        ),
        exits={"east": MOON_ELF_START_ROOM_KEY},
        npc_keys=("moon_elf_journal_keeper",),
        tags=("safe", "journals", "library", "family_history", "quiet"),
    ),
    RoomDefinition(
        key=MOON_ELF_MOONMIRROR_WALK_KEY,
        name="Moonmirror Walk",
        region_key=MOON_ELF_REGION_KEY,
        description=(
            "A narrow promenade follows the outside edge of the civic ridge. Tall metal frames hold adjustable mirrors and polished dark plates used for teaching observation, comparing angles, and carrying moonlight into shaded courtyards below. None of them claims to predict the future. "
            "The walk is beautiful because it is useful: silvered surfaces catch pieces of sky, while carefully placed seats let people compare how the same mountain looks from several positions."
        ),
        exits={"west": MOON_ELF_SKYCOURT_KEY, "south": MOON_ELF_WIND_TERRACE_KEY},
        tags=("safe", "moonlight", "mirrors", "observation", "promenade"),
    ),
    RoomDefinition(
        key=MOON_ELF_NIGHT_MARKET_KEY,
        name="Lantern Market",
        region_key=MOON_ELF_REGION_KEY,
        description=(
            "A compact market terrace nestles behind stone wind screens east of the plaza. Vendors sell hot tea, baked mountain roots, folded breads, wool, ink, polished metalwork, glass, climbing gear, fruit brought up from lower valleys, and small luxuries meant to be enjoyed rather than interpreted. "
            "Musicians favor strings and soft hand percussion that carry without fighting the wind. The market becomes busier after sunset, when people finish work and the high city settles into its preferred evening rhythm."
        ),
        exits={"west": MOON_ELF_START_ROOM_KEY, "east": MOON_ELF_SPIRE_LOBBY_KEY},
        tags=("safe", "market", "nightlife", "food", "music", "pleasant"),
    ),
    RoomDefinition(
        key=MOON_ELF_WIND_TERRACE_KEY,
        name="Wind Terrace",
        region_key=MOON_ELF_REGION_KEY,
        description=(
            "A stepped residential terrace rises above the central plaza, planted with hardy flowers, dwarf pines, sheltered herb beds, and little courts where neighbors share tables out of the strongest wind. Tuned metal chimes hang beneath several eaves, not as charms but as practical weather indicators whose pitch changes before a front crosses the ridge. "
            "From here, the city feels lived in rather than ceremonial: laundry dries behind screens, children race along the inner stairs, and older residents argue amiably about whether tonight will actually stay clear."
        ),
        exits={
            "down": MOON_ELF_START_ROOM_KEY,
            "north": MOON_ELF_MOONMIRROR_WALK_KEY,
            "east": MOON_ELF_HORIZON_DECK_KEY,
        },
        tags=("safe", "residential", "weather", "gardens", "high_city"),
    ),
    RoomDefinition(
        key=MOON_ELF_SPIRE_LOBBY_KEY,
        name="Skyglass Spire Vestibule",
        region_key=MOON_ELF_REGION_KEY,
        description=(
            "The base of Skyglass Spire opens into a tall vestibule ribbed in pale stone and dark metal. Vertical windows reveal only fragments of the tower above, making its scale difficult to judge from inside. A directory lists residences, studios, observatory floors, public terraces, maintenance levels, and the Horizon Deck near the crown. "
            "Counterweighted ascent cages move quietly in enclosed shafts, their mechanisms concealed behind carved panels except where inspection windows expose cables, brakes, and enormous balanced stones."
        ),
        exits={"west": MOON_ELF_NIGHT_MARKET_KEY, "up": MOON_ELF_HORIZON_DECK_KEY},
        npc_keys=("moon_elf_spire_attendant",),
        tags=("safe", "skyscraper", "spire", "vertical_city", "transit"),
    ),
    RoomDefinition(
        key=MOON_ELF_HORIZON_DECK_KEY,
        name="Horizon Deck",
        region_key=MOON_ELF_REGION_KEY,
        description=(
            "The public deck near the crown of Skyglass Spire circles the tower in a broad ring of stone, skyglass, and sheltered viewing bays. The entire starter city is visible below: Skycourt benches, mirror frames, market lamps, terraced roofs, and the ridge roads dropping toward distant valleys. "
            "Above the public deck, a private ascent continues to the High Aerie Penthouse. Its upper balconies are visible through the tower ribs, close enough to feel real and high enough to remain unmistakably separate from the public route."
        ),
        exits={
            "down": MOON_ELF_SPIRE_LOBBY_KEY,
            "west": MOON_ELF_WIND_TERRACE_KEY,
            "up": MOON_ELF_PENTHOUSE_KEY,
        },
        tags=("safe", "observation", "public_lookout", "spire", "penthouse_below"),
    ),
    RoomDefinition(
        key=MOON_ELF_PENTHOUSE_KEY,
        name="High Aerie Penthouse",
        region_key=MOON_ELF_REGION_KEY,
        description=(
            "At the crown of Skyglass Spire, a private residence opens around a moonward salon with broad curved windows and doors onto sheltered balconies. A private observatory occupies one side of the suite; comfortable living rooms, sleeping chambers, a kitchen, and a planted rooftop court occupy the other. "
            "The height is dramatic without making the space cold. Fire-warmed stone, deep seating, bookshelves, blankets, and protected greenery make it a place intended to be lived in while the whole of High Horizon glitters below."
        ),
        exits={"down": MOON_ELF_HORIZON_DECK_KEY},
        tags=("safe", "private_home", "penthouse", "skyscraper", "future_player_home", "luxury"),
    ),
)


HORIZON_STEWARD = NpcDefinition(
    key="moon_elf_horizon_steward",
    name="Horizon Steward",
    short_description="a civic steward arranging petitions into arguments for, against, and not yet answered",
    room_key=MOON_ELF_SKYCOURT_KEY,
    role="Horizon Council steward and civic-government guide",
    dialogue=(
        "The steward taps the opposing column on a public slate. 'If I cannot state the strongest case against my own proposal, I am not ready to ask the city to live under it.'",
        "'Changing a vote after the evidence changes is not losing. Pretending the evidence did not change is losing.'",
        "'The Council governs roads, water, trade rules, public works, and disputes. It does not tell the moon what to mean, and the moon does not tell us how to vote.'",
    ),
)

JOURNAL_KEEPER = NpcDefinition(
    key="moon_elf_journal_keeper",
    name="Journal Keeper",
    short_description="a patient keeper repairing bindings beside a stack of family volumes",
    room_key=MOON_ELF_JOURNAL_GALLERY_KEY,
    role="keeper of voluntary family and civic journals",
    dialogue=(
        "The keeper threads a new ribbon through an old binding. 'A correction does not ruin the earlier page. It tells you where the view changed.'",
        "'Some families publish everything. Some keep nearly everything private. A tradition about perspective is not an excuse to abolish privacy.'",
    ),
)

SPIRE_ATTENDANT = NpcDefinition(
    key="moon_elf_spire_attendant",
    name="Spire Attendant",
    short_description="an attendant watching the ascent indicators and keeping visitors on the public levels",
    room_key=MOON_ELF_SPIRE_LOBBY_KEY,
    role="Skyglass Spire public-route attendant",
    dialogue=(
        "The attendant glances up the impossible height of the shaft. 'Public deck near the crown. Private floors stay private. Height is not an invitation.'",
        "'Yes, the top suite is a penthouse. We have a perfectly good word for a residence at the top of a very tall building.'",
    ),
)

MOON_ELF_CITY_NPCS = (HORIZON_STEWARD, JOURNAL_KEEPER, SPIRE_ATTENDANT)


def _feature(
    key: str,
    name: str,
    summary: str,
    examine: str,
    *,
    aliases: tuple[str, ...] = (),
    search: str = "",
    touch: str = "",
    listen: str = "",
) -> FeatureDefinition:
    return FeatureDefinition(
        key=key,
        name=name,
        aliases=aliases,
        summary=summary,
        examine_text=examine,
        search_text=search,
        touch_text=touch,
        listen_text=listen,
    )


def _exit(direction: str, destination: str, name: str, text: str, **kwargs) -> ExitDefinition:
    return ExitDefinition(direction=direction, destination_key=destination, name=name, travel_text=text, **kwargs)


def _day(text: str) -> DescriptionLayer:
    return DescriptionLayer(
        "moon_elf_day",
        text,
        priority=40,
        condition=ViewCondition(time_buckets=("day",)),
    )


def _night(text: str) -> DescriptionLayer:
    return DescriptionLayer(
        "moon_elf_night",
        text,
        priority=50,
        condition=ViewCondition(time_buckets=("night",)),
    )


def moon_elf_city_augmentations() -> dict[str, RoomAugmentation]:
    penthouse_access = ViewCondition(required_flags=(MOON_ELF_PENTHOUSE_ACCESS_FLAG,))
    return {
        MOON_ELF_START_ROOM_KEY: RoomAugmentation(
            exit_overrides=(
                _exit("north", MOON_ELF_SKYCOURT_KEY, "The Skycourt", "You climb the shallow public steps toward the civic court."),
                _exit("west", MOON_ELF_JOURNAL_GALLERY_KEY, "Journal Gallery", "You pass beneath a row of hanging reading lamps into the journal arcade."),
                _exit("east", MOON_ELF_NIGHT_MARKET_KEY, "Lantern Market", "You follow the smell of tea and warm bread east behind the wind screens."),
                _exit("up", MOON_ELF_WIND_TERRACE_KEY, "Wind Terrace", "You climb the broad residential stairs toward the higher gardens."),
            ),
            features=(
                _feature("horizon_rail", "Horizon Rail", "a low bronze rail engraved with the names of distant peaks and passes", "The rail is a practical sighting guide. Small notches line up with roads, watch posts, weather stations, and mountain summits visible on a clear day.", aliases=("rail", "horizon rail", "sighting rail")),
                _feature("phase_dial", "Moon Phase Dial", "a simple civic dial showing the current phase of Astralis's moon", "The dial records the same four-phase cycle used by the calendar. A small plaque explicitly calls the phases customs of reflection, not predictions of fate.", aliases=("dial", "moon dial", "phase dial", "moon phase dial")),
                _feature("distant_spire", "Skyglass Spire", "the city's tallest tower rising far above the ridge", "Even from the plaza, the tower reads as a vertical city in miniature: stacked balconies, public decks, residences, gardens, and observatory levels. The crown holds a private penthouse above the public Horizon Deck.", aliases=("spire", "skyglass spire", "tower", "skyscraper")),
            ),
            description_layers=(
                _day("In daylight, High Horizon is bright and practical: messengers cross the plaza, shutters angle against the sun, and the surrounding ranges seem close enough to touch."),
                _night("After sunset, the plaza grows more social rather than less. Shielded lamps, tea tables, quiet music, and long conversations turn the ridge into a place people clearly enjoy inhabiting."),
            ),
        ),
        MOON_ELF_SKYCOURT_KEY: RoomAugmentation(
            exit_overrides=(
                _exit("south", MOON_ELF_START_ROOM_KEY, "High Horizon Plaza", "You leave the speaking floor and descend to the central plaza."),
                _exit("east", MOON_ELF_MOONMIRROR_WALK_KEY, "Moonmirror Walk", "You step east from civic debate onto the ridge promenade."),
            ),
            features=(
                _feature("rotating_roster", "Rotating Council Roster", "a public board listing current stewards and the dates their terms turn over", "The terms are staggered so the entire council cannot be replaced at once. No family owns a seat, and the rotation schedule is a civic calendar rather than a lunar omen.", aliases=("roster", "council roster", "steward board", "term board")),
                _feature("counterview_floor", "Counterview Floor", "a marked half-circle opposite the ordinary speaking position", "For major proposals, the principal advocate crosses to this mark and states the strongest serious argument against their own position before debate continues. It makes perspective a procedure instead of a slogan.", aliases=("counterview", "counterview floor", "opposing mark", "marked floor")),
                _feature("revision_ledger", "Revision Ledger", "an open civic ledger recording why major decisions were made and what could reopen them", "Each entry names the evidence considered, dissenting views, the final decision, and conditions that would justify review. Several entries end with later corrections rather than pretending the first decision was eternal.", aliases=("ledger", "revision ledger", "decision ledger", "civic ledger")),
            ),
            description_layers=(
                _day("Day sessions are brisk and administrative, with road maintenance, water storage, trade rules, and building petitions taking most of the floor time."),
                _night("Evening sessions draw more onlookers. The court remains quiet enough that disagreement sounds conversational rather than theatrical."),
            ),
        ),
        MOON_ELF_JOURNAL_GALLERY_KEY: RoomAugmentation(
            exit_overrides=(
                _exit("east", MOON_ELF_START_ROOM_KEY, "High Horizon Plaza", "You leave the reading alcoves and return east to the plaza."),
            ),
            features=(
                _feature("family_cabinets", "Family Cabinets", "rows of lockable cabinets holding private and donated generational journals", "Different families set different access rules. Some shelves are public, some open only to relatives, and some remain sealed until a date written into the binding agreement.", aliases=("cabinets", "family journals", "journal cabinets", "shelves")),
                _feature("correction_ribbons", "Correction Ribbons", "colored ribbons linking old entries to later revisions", "A blue ribbon means later evidence changed the conclusion; silver marks a remembered disagreement; white indicates a writer who explicitly withdrew an earlier claim. The old page stays intact.", aliases=("ribbons", "correction ribbons", "markers", "journal ribbons")),
            ),
            description_layers=(
                _day("Window shutters stand wide, and readers move their chairs as the sun shifts across the valley."),
                _night("Warm reading lamps turn the gallery into one of the coziest rooms on the ridge while the black mountain windows reflect shelves back into themselves."),
            ),
        ),
        MOON_ELF_MOONMIRROR_WALK_KEY: RoomAugmentation(
            exit_overrides=(
                _exit("west", MOON_ELF_SKYCOURT_KEY, "The Skycourt", "You follow the mirror frames west toward the civic benches."),
                _exit("south", MOON_ELF_WIND_TERRACE_KEY, "Wind Terrace", "The promenade slopes south toward gardens and residential stairs."),
            ),
            features=(
                _feature("teaching_mirrors", "Teaching Mirrors", "adjustable silvered frames used to compare reflected angles", "The frames are mounted with simple degree marks and alignment pins. Students can stand at different points and compare how one object appears under changed distance and angle.", aliases=("mirrors", "teaching mirrors", "mirror frames", "silvered frames")),
                _feature("moonlight_channels", "Moonlight Channels", "shallow polished channels carrying reflected light toward lower courtyards", "On clear nights, selected mirrors direct soft moonlight into shaded stairs and garden courts. The system is civic lighting with philosophical aesthetics, not a magical oracle.", aliases=("channels", "moonlight channels", "light channels")),
            ),
            description_layers=(
                _day("Most mirrors are folded partly inward against the bright sun, leaving the promenade to walkers and students measuring distant landmarks."),
                _night("The frames wake visually after dark, catching fragments of moon and city light while the valley below disappears into depth."),
            ),
        ),
        MOON_ELF_NIGHT_MARKET_KEY: RoomAugmentation(
            exit_overrides=(
                _exit("west", MOON_ELF_START_ROOM_KEY, "High Horizon Plaza", "You leave the sheltered stalls and return west to the plaza."),
                _exit("east", MOON_ELF_SPIRE_LOBBY_KEY, "Skyglass Spire Vestibule", "You follow the market terrace east to the foot of the great tower."),
            ),
            features=(
                _feature("tea_counter", "Mountain Tea Counter", "a long stone counter crowded with steaming cups and small plates", "The menu is ordinary and inviting: bitter black tea, sweet herb tea, folded bread, soft cheese, roast roots, preserved fruit, and honey cakes brought up from lower farms.", aliases=("tea", "tea counter", "food counter", "counter"), listen="Cups click against stone while three neighboring tables conduct three unrelated arguments."),
                _feature("music_nook", "Music Nook", "a sheltered corner where small groups play strings and hand percussion", "The musicians are not performing a ritual. They take requests, stop for food, argue about tempo, and rotate when the wind makes one corner too cold.", aliases=("music", "musicians", "music nook", "players"), listen="Plucked strings and soft drum taps carry just far enough to give the market a pulse."),
            ),
            description_layers=(
                _day("Only part of the market is open during the brightest hours, mostly practical stalls serving workers crossing the ridge."),
                _night("After sunset the terrace fills comfortably rather than chaotically, with food, music, shopping, gossip, and people lingering because there is nowhere they urgently need to be."),
            ),
        ),
        MOON_ELF_WIND_TERRACE_KEY: RoomAugmentation(
            exit_overrides=(
                _exit("down", MOON_ELF_START_ROOM_KEY, "High Horizon Plaza", "You descend the broad stairs to the central plaza."),
                _exit("north", MOON_ELF_MOONMIRROR_WALK_KEY, "Moonmirror Walk", "You climb north toward the ridge-edge promenade."),
                _exit("east", MOON_ELF_HORIZON_DECK_KEY, "Horizon Deck", "A high bridgewalk leads east toward the public deck of Skyglass Spire."),
            ),
            features=(
                _feature("weather_chimes", "Weather Chimes", "tuned metal strips whose pitch and movement make changes in the wind easy to notice", "The chimes are calibrated rather than mystical. Residents know which rattling crosswind usually precedes rain from the west and which clear note simply means cold air is falling from the higher snowfields.", aliases=("chimes", "weather chimes", "wind chimes"), listen="A few low notes answer the current breeze without forming anything like a melody."),
                _feature("shared_gardens", "Shared Terrace Gardens", "protected beds of herbs, flowers, and dwarf trees tucked behind wind screens", "Stone walls capture warmth for plants that would struggle in the exposed ridge air. Neighbors share watering and pruning without turning every garden into a formal civic project.", aliases=("gardens", "terrace gardens", "herbs", "plants")),
            ),
            description_layers=(
                _day("Children use the inner stairs as shortcuts while gardeners angle screens to give the beds a few more hours of sun."),
                _night("Lanterns glow behind residential shutters and the terrace smells of warm stone, herbs, and dinners being finished late."),
            ),
        ),
        MOON_ELF_SPIRE_LOBBY_KEY: RoomAugmentation(
            exit_overrides=(
                _exit("west", MOON_ELF_NIGHT_MARKET_KEY, "Lantern Market", "You step out of the tower and back into the sheltered market terrace."),
                _exit("up", MOON_ELF_HORIZON_DECK_KEY, "Horizon Deck", "You take a public ascent cage toward the upper observation levels."),
            ),
            features=(
                _feature("vertical_directory", "Vertical Directory", "a floor-by-floor map of the tower's residences, studios, gardens, and observatories", "The directory makes the tower's scale explicit. It is not a single monument with an observation room on top; it is an inhabited high-rise with dozens of useful levels.", aliases=("directory", "tower directory", "floor map", "floors")),
                _feature("ascent_cages", "Ascent Cages", "quiet counterweighted passenger cages moving through enclosed shafts", "Inspection windows show braided cable, braking teeth, guide rails, and enormous stone counterweights. The engineering is elegant because it is maintained, not because the mechanisms are hidden behind magic.", aliases=("cages", "lifts", "elevators", "ascent cages"), listen="Far above, a soft bell marks a cage arriving at another floor."),
            ),
            description_layers=(
                _day("Residents, couriers, and observatory workers share the public cages with visitors headed for the Horizon Deck."),
                _night("The vestibule grows quieter but never closes; the tower is residential, and people keep coming home long after the market begins to thin."),
            ),
        ),
        MOON_ELF_HORIZON_DECK_KEY: RoomAugmentation(
            exit_overrides=(
                _exit("down", MOON_ELF_SPIRE_LOBBY_KEY, "Skyglass Spire Vestibule", "You ride the public cage down toward the tower's lower levels."),
                _exit("west", MOON_ELF_WIND_TERRACE_KEY, "Wind Terrace", "You take the high bridgewalk west toward the residential terraces."),
                ExitDefinition(
                    direction="up",
                    destination_key=MOON_ELF_PENTHOUSE_KEY,
                    name="High Aerie Penthouse",
                    travel_text="Your private ascent key answers, and the last cage carries you above the public deck into the High Aerie Penthouse.",
                    failure_text="The private ascent does not answer. The High Aerie Penthouse is a residence, not part of the public observation route.",
                    condition=penthouse_access,
                    hidden_when_unavailable=False,
                ),
            ),
            features=(
                _feature("ridge_panorama", "Ridge Panorama", "a nearly complete view of High Horizon and the surrounding Moon Peaks", "From here the city's planning becomes obvious: open plazas, terraced roofs, mirror walks, windbreak walls, and public sight lines all preserve different ways of seeing the same landscape.", aliases=("panorama", "view", "ridge panorama", "city view")),
                _feature("viewing_lenses", "Viewing Lenses", "public mounted lenses aimed at roads, passes, weather stations, and distant summits", "Each lens is labeled with what it is actually for. The city considers accurate distance viewing useful enough that nobody needs to dress it up as divination.", aliases=("lenses", "viewing lenses", "telescopes", "scopes")),
                _feature("private_ascent", "Private Ascent", "a separate cage and stair behind a locked skyglass door leading to the penthouse above", "A small plaque reads HIGH AERIE - PRIVATE RESIDENCE. There is no ceremonial warning and no claim that the resident is politically important. It is simply a very desirable home at the top of a skyscraper.", aliases=("private ascent", "penthouse lift", "private lift", "skyglass door")),
            ),
            description_layers=(
                _day("Sunlight turns distant snowfields painfully bright while the city below looks compact and carefully ordered."),
                _night("At night, the deck earns its name. High Horizon becomes a field of warm lights beneath an enormous dark sky, with no sense that the world below has become less important."),
            ),
        ),
        MOON_ELF_PENTHOUSE_KEY: RoomAugmentation(
            exit_overrides=(
                _exit("down", MOON_ELF_HORIZON_DECK_KEY, "Horizon Deck", "You take the private ascent down to the public Horizon Deck."),
            ),
            features=(
                _feature("moonward_salon", "Moonward Salon", "a broad living room wrapped in curved windows, bookshelves, and deep seating", "The room is luxurious without becoming sterile: low tables, layered rugs, books, blankets, warm lamps, and a long hearth make the enormous view feel like part of a home rather than a museum.", aliases=("salon", "living room", "moonward salon", "windows")),
                _feature("private_observatory", "Private Observatory", "a compact observatory built into the highest enclosed corner of the suite", "The instruments are for astronomy, weather, distant roads, and the pleasure of looking. A writing desk beside them makes it easy to record a view and later admit that the first interpretation was wrong.", aliases=("observatory", "private observatory", "instruments", "telescope")),
                _feature("rooftop_court", "Sheltered Rooftop Court", "a private high garden protected by skyglass wind screens", "Hardy flowers, fragrant herbs, a small tree, and comfortable seats occupy the warmest pockets of the court. The roof is designed for evenings spent outside, not merely dramatic photographs.", aliases=("garden", "rooftop garden", "rooftop court", "court")),
            ),
            description_layers=(
                _day("The suite fills with reflected mountain light while the tower throws a narrow shadow across the ridge far below."),
                _night("The private rooms glow warmly against the glass. Below, the whole city remains visible as an inhabited place rather than a collection of landmarks."),
            ),
        ),
    }


def _patch_moon_elf_city_lore() -> None:
    current = character_options.RACES_BY_KEY.get("moon_elf")
    if current is None:
        return
    extra = (
        "Their principal starter city is High Horizon, a pleasant high-ridge city of open plazas, terraced homes, mirror walks, night markets, and broad views.",
        "High Horizon is governed by the Horizon Council, a small rotating council of civic stewards with staggered non-hereditary terms.",
        "Before major votes, advocates are expected to present the strongest Counterview against their own position, and decisions record what evidence could justify later revision.",
        "Skyglass Spire is the city's tallest inhabited tower, a fantasy skyscraper containing residences, observatories, public decks, and the private High Aerie Penthouse at its crown.",
    )
    lore = current.lore + tuple(line for line in extra if line not in current.lore)
    replacement = replace(
        current,
        description=(
            "Lavender-grey elves with oversized eyes and no visible sclera, shaped by an ancient lunar culture of perspective, revision, and long horizons. Their high-ridge cities are elegant, comfortable, and deeply lived in."
        ),
        lore=lore,
    )
    character_options.RACES = tuple(
        replacement if race.key == "moon_elf" else race for race in character_options.RACES
    )
    character_options.RACES_BY_KEY["moon_elf"] = replacement


def install_moon_elf_city_content(world_service=None) -> None:
    """Register High Horizon, its civic government, and Skyglass Spire."""
    _patch_moon_elf_city_lore()

    known_rooms = set(legacy_world.ROOMS_BY_KEY)
    additions = tuple(room for room in MOON_ELF_ROOMS if room.key not in known_rooms)
    if additions:
        legacy_world.ROOMS = legacy_world.ROOMS + additions
    legacy_world.ROOMS_BY_KEY.update({room.key: room for room in MOON_ELF_ROOMS})

    known_npcs = set(legacy_world.NPCS_BY_KEY)
    for npc in MOON_ELF_CITY_NPCS:
        if npc.key not in known_npcs:
            legacy_world.NPCS = legacy_world.NPCS + (npc,)
            known_npcs.add(npc.key)
        legacy_world.NPCS_BY_KEY[npc.key] = npc

    if world_service is not None:
        world_service.legacy_rooms.update({room.key: room for room in MOON_ELF_ROOMS})
        world_service.augmentations.update(moon_elf_city_augmentations())
        cache = getattr(world_service, "_scene_cache", None)
        if cache is not None:
            for room_key in MOON_ELF_CITY_ROOM_KEYS:
                cache.pop(room_key, None)


def _prepare_moon_elf_city(session) -> bool:
    if session.character is None or session.character.race != "moon_elf":
        return False

    character_id = session.character.id
    changed = False
    if not session.character.current_room:
        session.database.set_character_room(character_id, MOON_ELF_START_ROOM_KEY)
        changed = True

    if not session.character.bind_room:
        bind_target = session.character.current_room or MOON_ELF_START_ROOM_KEY
        session.database.set_bind_room(character_id, bind_target)
        changed = True

    if changed:
        refreshed = session.database.get_character_by_name(session.character.name)
        if refreshed is not None:
            session.character = refreshed

    return changed


async def _show_lines(session, title: str, lines: tuple[str, ...]) -> None:
    await session.send(f"\r\n--- {title} ---\r\n")
    for line in lines:
        await session.send(line + "\r\n")


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


def install_moon_elf_city_runtime(player_session_class, world_service) -> None:
    install_moon_elf_city_content(world_service)
    if getattr(player_session_class, "_moon_elf_city_runtime_installed", False):
        return

    previous_enter_character = player_session_class.enter_character
    previous_playing_prompt = player_session_class.playing_prompt

    async def enter_character(self) -> None:
        if self.character is not None and self.character.race == "moon_elf":
            _prepare_moon_elf_city(self)
        await previous_enter_character(self)
        if self.character is None or self.character.race != "moon_elf":
            return

        _prepare_moon_elf_city(self)
        flags = self.database.list_flags(self.character.id)
        if MOON_ELF_CITY_INTRO_FLAG not in flags:
            self.database.grant_flag(self.character.id, MOON_ELF_CITY_INTRO_FLAG)
            await self.send(
                "\r\nHigh Horizon is home: a high-ridge Moon Elf city built around open sky, long views, lived-in terraces, quiet nightlife, and the belief that perspective is useful only if it changes how people actually behave.\r\n"
                "North is the public Skycourt of the rotating Horizon Council. East, the Lantern Market leads toward Skyglass Spire and the private penthouse at its crown. Type CITY or GOVERNMENT for an overview.\r\n"
            )

    async def playing_prompt(self) -> None:
        if self.character is None or self.character.race != "moon_elf":
            await previous_playing_prompt(self)
            return

        await self.send_client_state()
        command = await self.prompt("\r\n> ")
        if command is None:
            self.state = type(self.state).DISCONNECTED
            return
        normalized = command.strip().lower()

        if normalized in {"city", "high horizon", "starter city", "moon elf city", "moon city"}:
            await _show_lines(self, "High Horizon", CITY_LINES)
            return
        if normalized in {"government", "council", "horizon council", "government of high horizon"}:
            await _show_lines(self, "Horizon Council", GOVERNMENT_LINES)
            return
        if normalized in {"counterview", "counter view", "argue against", "opposing view"}:
            await self.send("\r\n--- Counterview ---\r\n")
            await self.send(
                "Before a major vote, the strongest advocate for a proposal must state the strongest serious case against it. The purpose is not ritual humility; it is to prove the decision-maker understands what would make their own preferred answer wrong.\r\n"
            )
            if self.character.current_room == MOON_ELF_SKYCOURT_KEY:
                await self.send(
                    "Standing in the Skycourt, you can see the Counterview mark on the speaking floor opposite the ordinary lectern.\r\n"
                )
            return
        if normalized in {"spire", "skyglass spire", "skyscraper", "tower"}:
            await _show_lines(self, "Skyglass Spire", SPIRE_LINES)
            return
        if normalized in {"penthouse", "high aerie", "high aerie penthouse", "my penthouse", "suite"}:
            await _show_lines(self, "High Aerie Penthouse", PENTHOUSE_LINES)
            flags = self.database.list_flags(self.character.id)
            if MOON_ELF_PENTHOUSE_ACCESS_FLAG in flags:
                await self.send("Your private ascent access is active. From the Horizon Deck, travel UP.\r\n")
            else:
                await self.send(
                    "The private ascent is not yet unlocked for this character. The suite remains visible above the public Horizon Deck.\r\n"
                )
            return

        await _delegate_prompt(self, previous_playing_prompt, command)

        if normalized in {"help", "?"}:
            await self.send(
                "Moon Elf city commands: CITY describes High Horizon; GOVERNMENT explains the rotating Horizon Council; COUNTERVIEW explains its debate rule; SPIRE describes the fantasy skyscraper; PENTHOUSE describes the High Aerie suite.\r\n"
            )

    player_session_class.enter_character = enter_character
    player_session_class.playing_prompt = playing_prompt
    player_session_class._moon_elf_city_runtime_installed = True
