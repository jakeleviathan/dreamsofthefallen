from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Awaitable, Callable

from mud.astralis_calendar import AstralisCalendarDate
from mud.astralis_time import ASTRALIS_CLOCK, AstralisMoment


@dataclass(frozen=True, slots=True)
class SeasonalCultureAnchor:
    key: str
    race_key: str
    region_key: str
    season_key: str
    title: str
    feature_name: str
    aliases: tuple[str, ...]
    ambient_text: str
    examine_text: str
    touch_text: str
    listen_text: str
    smell_text: str
    use_text: str
    start_event: str
    end_event: str

    def active(self, calendar: AstralisCalendarDate) -> bool:
        return calendar.season_key == self.season_key

    def matches(self, target: str) -> bool:
        normalized = target.strip().lower()
        values = {
            self.key.replace("_", " "),
            self.title.lower(),
            self.feature_name.lower(),
            *(value.lower() for value in self.aliases),
        }
        return normalized in values

    def observation_flag(self, year: int) -> str:
        return f"seasonal_anchor:{self.key}:year:{year}"


SEASONAL_CULTURE_ANCHORS: tuple[SeasonalCultureAnchor, ...] = (
    SeasonalCultureAnchor(
        key="blackwall_hearths",
        race_key="human",
        region_key="human_kingdom",
        season_key="winter",
        title="Blackwall Hearths",
        feature_name="Winter Hearths",
        aliases=("hearth", "hearths", "winter hearth", "braziers", "brazier", "blackwall hearths"),
        ambient_text=(
            "Winter braziers burn at corners, gates, and watch posts. The city treats the cold as another civic problem to be organized: iron baskets are fed on schedules, guards warm their hands between rounds, and shop doors wear heavy heat curtains."
        ),
        examine_text=(
            "The Blackwall winter hearths are practical iron baskets rather than ceremonial fires. Chalk marks on nearby stone record fuel deliveries and watch rotations, turning warmth itself into part of the city's bureaucracy."
        ),
        touch_text="Heat rolls off the iron basket hard enough to sting your palms before you get close to the coals.",
        listen_text="Coal settles with dry clicks beneath the low roar of flame; nearby boots pause, warm, and move on.",
        smell_text="Coal smoke, hot iron, damp wool, and winter air mingle around the hearth.",
        use_text="You stop at the Blackwall hearth long enough to warm yourself and watch the city's winter rhythm pass around you.",
        start_event="Winter reaches the Human Kingdom. Blackwall crews roll iron hearths into the streets and begin feeding the first braziers of the season.",
        end_event="The last Blackwall winter hearths are allowed to go dark as the cold season releases its hold on the city.",
    ),
    SeasonalCultureAnchor(
        key="firstgreen",
        race_key="forest_elf",
        region_key="great_elf_forest",
        season_key="spring",
        title="Firstgreen",
        feature_name="Firstgreen Growth",
        aliases=("firstgreen", "first green", "new leaves", "buds", "spring growth", "willow markers"),
        ambient_text=(
            "Firstgreen has begun. New leaves show almost translucent at their edges, and the Druidic Circles mark safe paths with fresh willow switches so travelers can distinguish spring growth from older trail signs."
        ),
        examine_text=(
            "The newest leaves are bright, soft, and almost luminous against last season's darker wood. Small willow markers have been tied where paths divide, simple enough to disappear naturally as the season advances."
        ),
        touch_text="The new leaf is cool and tender beneath one fingertip, its surface still softer than the mature canopy around it.",
        listen_text="Spring water moves faster beneath the forest sounds, and birds answer one another from territory newly filled with leaves.",
        smell_text="Wet bark, opening leaves, young grass, and cold running water make the forest smell newly awake.",
        use_text="You pause to read the fresh willow markers and the new growth together, learning how the forest's spring paths announce themselves.",
        start_event="Firstgreen arrives in the Great Elven Forest. New leaves open across the canopy, and fresh willow markers begin appearing along the old paths.",
        end_event="The bright Firstgreen leaves deepen toward summer color, and the temporary willow path markers begin to disappear into ordinary growth.",
    ),
    SeasonalCultureAnchor(
        key="long_moon",
        race_key="moon_elf",
        region_key="moon_peaks",
        season_key="winter",
        title="The Long Moon",
        feature_name="Moon Mirrors",
        aliases=("long moon", "moon mirror", "moon mirrors", "mirrors", "silver mirrors", "winter mirrors"),
        ambient_text=(
            "Winter in the Moon Peaks is called the Long Moon. Thin silver mirrors appear on high balconies and sheltered ledges, angled to catch moonlight for as many hours as the mountain horizon allows."
        ),
        examine_text=(
            "The mirrors are narrow polished plates, elegant but functional. Each is set at a slightly different angle so moonlight can be followed across the peaks rather than captured in one fixed direction."
        ),
        touch_text="The metal is painfully cold, smooth enough that your fingertip leaves a brief haze before the mountain air clears it.",
        listen_text="The mirrors themselves are silent, but their hanging fittings give tiny crystalline ticks whenever the high wind changes direction.",
        smell_text="The air around the mirrors is nearly scentless: cold stone, snow, and the faint mineral sharpness of polished metal.",
        use_text="You adjust your position until the reflected moonlight reaches your eyes, understanding for a moment why the high settlements measure winter by the moon as much as by the cold.",
        start_event="The Long Moon begins in the Moon Peaks. Silver moon mirrors are carried onto balconies and high ledges for the winter season.",
        end_event="As winter ends, the Moon Elves begin taking down the Long Moon mirrors, wrapping the polished plates for another year.",
    ),
    SeasonalCultureAnchor(
        key="deepfire_shift",
        race_key="dwarf",
        region_key="dwarven_mountain_industry",
        season_key="winter",
        title="Deepfire Shift",
        feature_name="Deepfire Boards",
        aliases=("deepfire", "deepfire shift", "shift board", "shift boards", "forge board", "boards"),
        ambient_text=(
            "The winter Deepfire Shift is in effect. Surface freight slows in the cold, so foundries and underground workshops post expanded shift boards and push more work through the mountain interior."
        ),
        examine_text=(
            "The Deepfire boards are dense with union marks, trade-house stamps, meal breaks, lift assignments, and furnace rotations. The remarkable part is not longer work so much as how precisely thousands of workers coordinate it."
        ),
        touch_text="The board is warm from the industrial air and gritty with chalk dust around the most frequently revised assignments.",
        listen_text="Steam valves vent, shift whistles answer one another, and freight chains continue moving long after surface traffic would normally thin.",
        smell_text="Hot metal, coal smoke, machine oil, bread from shift kitchens, and damp stone hang in the industrial air.",
        use_text="You study the Deepfire board until its stamps and shift marks resolve into a rough picture of how the winter city keeps itself moving.",
        start_event="Winter begins across the Dwarven settlements. Trade houses and unions post the first Deepfire shift boards as more work moves beneath the mountain.",
        end_event="Deepfire schedules are peeled from workshop boards as surface routes reopen and the winter industrial pattern relaxes.",
    ),
    SeasonalCultureAnchor(
        key="floodpick",
        race_key="goblin",
        region_key="junk_city_and_swamps",
        season_key="spring",
        title="Floodpick",
        feature_name="Floodpick Marks",
        aliases=("floodpick", "flood pick", "flood marks", "salvage marks", "pick marks", "chalk marks"),
        ambient_text=(
            "Spring floodwater rearranges the swamp margins, and Floodpick season begins. Goblins mark newly exposed salvage routes with quick chalk symbols, arguing cheerfully over which piles were discovered first and which are merely being rediscovered."
        ),
        examine_text=(
            "The Floodpick marks are fast, ugly, and extremely informative once you know the pattern: arrows for safe footing, circles for promising debris, teeth for contested salvage, and crossed hooks for piles already stripped clean."
        ),
        touch_text="The chalk is fresh enough to smear under your thumb; whoever made the mark passed this way recently.",
        listen_text="Somewhere nearby, metal is dragged out of mud while several voices loudly dispute the difference between finding something and owning it.",
        smell_text="Swamp water, wet wood, old metal, smoke, and churned mud dominate the spring air.",
        use_text="You follow the logic of the Floodpick marks until the apparent mess becomes a crude but effective map of fresh salvage opportunities.",
        start_event="Spring water rises around Junk City and the swamps. Fresh Floodpick marks begin appearing wherever the receding water exposes new salvage.",
        end_event="As spring flooding settles, the last useful Floodpick marks fade beneath traffic, rain, and newer claims.",
    ),
    SeasonalCultureAnchor(
        key="snow_trail",
        race_key="troll",
        region_key="troll_strongholds",
        season_key="winter",
        title="Snow Trail",
        feature_name="Snow Trail Markers",
        aliases=("snow trail", "snow trails", "trail marker", "trail markers", "bone markers", "winter trail"),
        ambient_text=(
            "Winter opens the Snow Trail network between deep-forest strongholds and tundra routes. Tall markers of wood, hide, and pale bone stand above the drifts where ordinary trail signs would vanish."
        ),
        examine_text=(
            "Each Snow Trail marker is deliberately oversized. Notches identify nearby strongholds, strips of hide show prevailing wind, and old tooth marks suggest that more than travelers use them to navigate."
        ),
        touch_text="The marker is rough, ice-cold, and solidly buried. Frozen hide straps have become nearly as rigid as the wood beneath them.",
        listen_text="Wind pulls at the hide streamers with a low snapping sound, carrying distant animal calls farther than the forest usually allows.",
        smell_text="Cold resin, hide, snow, smoke from distant camps, and the clean metallic smell of deep winter fill the air.",
        use_text="You line up the notches and wind-strips on the marker, learning how Troll travelers keep direction when snow erases the ground beneath them.",
        start_event="Winter settles over the Troll territories. Snow Trail markers rise above forest and tundra routes as seasonal travel shifts toward the old cold-weather paths.",
        end_event="The Snow Trail markers begin coming down as thawing ground reveals the older forest and stronghold paths again.",
    ),
    SeasonalCultureAnchor(
        key="quieting",
        race_key="undead",
        region_key="desert_necropolis",
        season_key="autumn",
        title="The Quieting",
        feature_name="Quieting Lamps",
        aliases=("quieting", "quieting lamp", "quieting lamps", "memorial lamps", "lamps", "funerary lamps"),
        ambient_text=(
            "Autumn brings the Quieting to the Necropolis. Small funerary lamps appear in thresholds and alcoves, not to mourn the dead as absent, but to acknowledge the lives they remember having before reanimation."
        ),
        examine_text=(
            "The lamps are intentionally small: bone, blackened bronze, stone, or old household metal depending on the family. Many bear two names—the name carried in life and the name used after reanimation."
        ),
        touch_text="The lamp gives off little heat. Its metal casing has been polished smooth by hands that return to it year after year.",
        listen_text="The Quieting is quieter than ordinary Necropolis life; conversations lower around the lamps, leaving soft footfalls and the faint movement of flame.",
        smell_text="Lamp oil, dry stone, old dust, and faint funerary resins linger around the alcoves.",
        use_text="You spend a moment before one of the Quieting lamps, reading the paired names and considering the continuity between a remembered life and an undead one.",
        start_event="Autumn reaches the Desert Necropolis. Quieting lamps begin appearing in doorways, crypt halls, and family alcoves throughout the city below.",
        end_event="The Quieting concludes. Funerary lamps are cleaned, extinguished, and returned to household niches until the next autumn.",
    ),
    SeasonalCultureAnchor(
        key="sporewake",
        race_key="sporekin",
        region_key="sporekin_underways",
        season_key="spring",
        title="Sporewake",
        feature_name="Sporewake Blooms",
        aliases=("sporewake", "spore wake", "blooms", "fruiting bodies", "spore blooms", "glowing mushrooms"),
        ambient_text=(
            "Sporewake moves through the Underways. Fruiting bodies brighten along old mycelial routes, and the shared consciousness carries a subtle sense of new growth even far below the surface."
        ),
        examine_text=(
            "The Sporewake growth is not one species but many responding together: shelf fungi, delicate caps, threadlike luminous growths, and tiny puffballs emerging along the same living network."
        ),
        touch_text="A nearby cap yields softly under your fingertip and gives off a dim pulse of light that travels a short distance into the surrounding mycelium.",
        listen_text="There is no single sound to the bloom, but water drops and tiny movements seem unusually synchronized in the living tunnels during Sporewake.",
        smell_text="Wet earth, mineral water, mushroom flesh, roots, and a faint sweet fermentation fill the Underways.",
        use_text="You rest your hand near the glowing growth until its tiny pulses join the larger rhythm of the shared network, briefly making the season feel less like a date than a sensation.",
        start_event="Spring reaches even the hidden Underways. Sporewake blooms brighten along the mycelial routes and the shared chorus swells with new growth.",
        end_event="Sporewake recedes as spring passes. The brightest fruiting bodies dim, leaving the deeper mycelial glow behind.",
    ),
)

ANCHORS_BY_KEY = {anchor.key: anchor for anchor in SEASONAL_CULTURE_ANCHORS}
ANCHORS_BY_REGION = {anchor.region_key: anchor for anchor in SEASONAL_CULTURE_ANCHORS}
ANCHORS_BY_RACE = {anchor.race_key: anchor for anchor in SEASONAL_CULTURE_ANCHORS}


def anchor_for_region(region_key: str) -> SeasonalCultureAnchor | None:
    return ANCHORS_BY_REGION.get(region_key)


def active_anchor_for_region(region_key: str, calendar: AstralisCalendarDate) -> SeasonalCultureAnchor | None:
    anchor = anchor_for_region(region_key)
    if anchor is None or not anchor.active(calendar):
        return None
    return anchor


def find_active_anchor(region_key: str, calendar: AstralisCalendarDate, target: str) -> SeasonalCultureAnchor | None:
    anchor = active_anchor_for_region(region_key, calendar)
    if anchor is None:
        return None
    return anchor if anchor.matches(target) else None


@dataclass(frozen=True, slots=True)
class SeasonalCultureEvent:
    region_key: str
    text: str
    category: str
    anchor_key: str


class SeasonalCultureService:
    """Broadcasts culture-specific changes when the Astralis season turns."""

    def __init__(self) -> None:
        self.last_season_key: str | None = None

    def initialize(self, moment: AstralisMoment) -> None:
        self.last_season_key = moment.calendar.season_key

    def sync(self, moment: AstralisMoment) -> tuple[SeasonalCultureEvent, ...]:
        current = moment.calendar.season_key
        if self.last_season_key is None:
            self.initialize(moment)
            return ()
        if current == self.last_season_key:
            return ()

        previous = self.last_season_key
        events: list[SeasonalCultureEvent] = []
        for anchor in SEASONAL_CULTURE_ANCHORS:
            if anchor.season_key == previous:
                events.append(
                    SeasonalCultureEvent(anchor.region_key, anchor.end_event, "seasonal_anchor_end", anchor.key)
                )
            if anchor.season_key == current:
                events.append(
                    SeasonalCultureEvent(anchor.region_key, anchor.start_event, "seasonal_anchor_start", anchor.key)
                )
        self.last_season_key = current
        return tuple(events)

    async def run(
        self,
        broadcast: Callable[[SeasonalCultureEvent], Awaitable[None]],
        *,
        interval_seconds: float = 5.0,
    ) -> None:
        if self.last_season_key is None:
            self.initialize(ASTRALIS_CLOCK.now())
        try:
            while True:
                await asyncio.sleep(interval_seconds)
                for event in self.sync(ASTRALIS_CLOCK.now()):
                    await broadcast(event)
        except asyncio.CancelledError:
            return


SEASONAL_CULTURES = SeasonalCultureService()
