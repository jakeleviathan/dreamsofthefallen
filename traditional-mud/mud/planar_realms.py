from __future__ import annotations

from dataclasses import dataclass, replace

import mud.crafting as crafting
import mud.world as legacy_world
from mud.astralis_time import ASTRALIS_CLOCK
from mud.crafting import ItemDefinition
from mud.gravewatch_keep import GRAVEWATCH_CASTELLAN_DEFEATED_FLAG, GRAVEWATCH_CRYPT_KEY
from mud.living_world import _chronicle_insert
from mud.sablewater_reach import SABLEWATER_DRIFTWOOD_SHRINE_KEY, SABLEWATER_ROOKERY_KEY
from mud.veyra_city import VEYRA_KEYHOUSE_KEY
from mud.veyra_underclock import UNDERCLOCK_COMPLETE_FLAG, UNDERCLOCK_MINUTE_KEY
from mud.waymeet_adventure_arc import ECHO_COMPLETE, ECHO_FIRST_BREATH_MARGIN
from mud.waymeet_frontier import WAYMEET_BROKEN_MILE_KEY
from mud.world import RoomDefinition


@dataclass(frozen=True, slots=True)
class PlaneDefinition:
    key: str
    name: str
    rarity: str
    rooms: tuple[str, ...]
    thesis: str
    chronicle_public: bool = True


def _room(key: str, name: str, region: str, description: str, exits: dict[str, str]) -> RoomDefinition:
    return RoomDefinition(
        key=key,
        name=name,
        region_key=region,
        description=description,
        exits=exits,
        enemy_keys=(),
        tags=("planar", "hidden_world", region),
    )


# The Pale — a bleached echo where discarded possibilities remain after people leave.
PALE = "plane_pale"
PALE_SHORE = "pale_colorless_shore"
PALE_STREET = "pale_uninhabited_street"
PALE_HOUSE = "pale_house_of_left_things"
PALE_BELL = "pale_bell_without_tower"
PALE_ROOMS = (PALE_SHORE, PALE_STREET, PALE_HOUSE, PALE_BELL)

# Brass Heaven — not divine: a dead city-sized machine whose builders are absent.
BRASS = "plane_brass_heaven"
BRASS_GATE = "brass_heaven_gate"
BRASS_AVENUE = "brass_heaven_processional"
BRASS_ORRERY = "brass_heaven_orchard_of_gears"
BRASS_THRONE = "brass_heaven_empty_throne"
BRASS_ROOMS = (BRASS_GATE, BRASS_AVENUE, BRASS_ORRERY, BRASS_THRONE)

# The Root Below — fungal wilderness that makes Sporekin antiquity look young.
ROOT = "plane_root_below"
ROOT_MOUTH = "root_below_mouth"
ROOT_FOREST = "root_below_lantern_forest"
ROOT_MEMORY = "root_below_memory_loam"
ROOT_HEART = "root_below_sleeping_heart"
ROOT_ROOMS = (ROOT_MOUTH, ROOT_FOREST, ROOT_MEMORY, ROOT_HEART)

# The Red Country — resembles fragments of Earth, but every familiar thing is wrong.
RED = "plane_red_country"
RED_ROAD = "red_country_road"
RED_STATION = "red_country_station"
RED_HOUSES = "red_country_identical_houses"
RED_TOWER = "red_country_water_tower"
RED_ROOMS = (RED_ROAD, RED_STATION, RED_HOUSES, RED_TOWER)

# The Sea Above — an ocean overhead with islands hanging downward from its surface.
SEA = "plane_sea_above"
SEA_BEACH = "sea_above_dry_beach"
SEA_PIER = "sea_above_upward_pier"
SEA_WRECK = "sea_above_hanging_wreck"
SEA_LIGHT = "sea_above_inverted_lighthouse"
SEA_ROOMS = (SEA_BEACH, SEA_PIER, SEA_WRECK, SEA_LIGHT)

# The Country Behind the Door — linked to the Red Door key but intentionally unexplained.
DOOR = "plane_country_behind_door"
DOOR_FIELD = "behind_door_white_field"
DOOR_VILLAGE = "behind_door_closed_village"
DOOR_HALL = "behind_door_long_hall"
DOOR_RED = "behind_door_other_red_door"
DOOR_ROOMS = (DOOR_FIELD, DOOR_VILLAGE, DOOR_HALL, DOOR_RED)

# The Unspoken — not advertised, not publicly chronicled, and perhaps not a place.
UNSPOKEN = "plane_unspoken"
UNSPOKEN_EDGE = "unspoken_edge"
UNSPOKEN_DISTANCE = "unspoken_distance"
UNSPOKEN_MOUTH = "unspoken_closed_mouth"
UNSPOKEN_LAST = "unspoken_last_place"
UNSPOKEN_ROOMS = (UNSPOKEN_EDGE, UNSPOKEN_DISTANCE, UNSPOKEN_MOUTH, UNSPOKEN_LAST)

PLANES = (
    PlaneDefinition(PALE, "The Pale", "rare", PALE_ROOMS, "Lost choices leave impressions here."),
    PlaneDefinition(BRASS, "Brass Heaven", "rare", BRASS_ROOMS, "A machine-city continues after its purpose died."),
    PlaneDefinition(ROOT, "The Root Below", "rare", ROOT_ROOMS, "The oldest fungal memory is still comparatively recent."),
    PlaneDefinition(RED, "The Red Country", "very_rare", RED_ROOMS, "It resembles Earth only enough to make recognition dangerous."),
    PlaneDefinition(SEA, "The Sea Above", "very_rare", SEA_ROOMS, "Gravity and horizon have reached a different agreement."),
    PlaneDefinition(DOOR, "The Country Behind the Door", "mythic", DOOR_ROOMS, "A country can exist behind something smaller than a country.", False),
    PlaneDefinition(UNSPOKEN, "The Unspoken", "mythic", UNSPOKEN_ROOMS, "No reliable source agrees that this is a place.", False),
)
PLANE_BY_ROOM = {room: plane for plane in PLANES for room in plane.rooms}

ROOMS = (
    _room(PALE_SHORE, "Colorless Shore", PALE, "A shore of white gravel meets a flat gray distance. Footprints appear beside yours, never ahead of them.", {"east": PALE_STREET}),
    _room(PALE_STREET, "Uninhabited Street", PALE, "Buildings imitate streets you almost remember. Their windows contain rooms after the people have left them.", {"west": PALE_SHORE, "east": PALE_HOUSE}),
    _room(PALE_HOUSE, "House of Left Things", PALE, "Tables hold gloves, keys, toys, letters and cups abandoned in other places. None cast a proper shadow.", {"west": PALE_STREET, "north": PALE_BELL}),
    _room(PALE_BELL, "Bell Without a Tower", PALE, "A bronze bell hangs from nothing. It rings only after you decide not to touch it.", {"south": PALE_HOUSE}),

    _room(BRASS_GATE, "Gate of Uncounted Teeth", BRASS, "A gate taller than Veyra opens one gear-tooth at a time beneath a copper sky.", {"east": BRASS_AVENUE}),
    _room(BRASS_AVENUE, "Processional of Silent Engines", BRASS, "Thousands of machines line a ceremonial avenue. Every flywheel is still. Every gauge reads READY.", {"west": BRASS_GATE, "east": BRASS_ORRERY}),
    _room(BRASS_ORRERY, "Orchard of Gears", BRASS, "Metal trees carry planetary mechanisms instead of fruit. Several orbit worlds that do not resemble Astralis.", {"west": BRASS_AVENUE, "north": BRASS_THRONE}),
    _room(BRASS_THRONE, "Empty Governor's Throne", BRASS, "A control throne faces a city with no operator. One small brass hand keeps pointing at you.", {"south": BRASS_ORRERY}),

    _room(ROOT_MOUTH, "Root Mouth", ROOT, "You stand within a hollow root wider than a city gate. Warm spores drift upward like slow sparks.", {"down": ROOT_FOREST}),
    _room(ROOT_FOREST, "Lantern Forest", ROOT, "Fungal trunks rise beyond sight, each carrying constellations of living lamps. The Chorus is audible here but cannot name this place.", {"up": ROOT_MOUTH, "east": ROOT_MEMORY}),
    _room(ROOT_MEMORY, "Memory Loam", ROOT, "Soft black earth releases impressions when stepped on: rain from ages with no names, hands of bodies with no known race.", {"west": ROOT_FOREST, "down": ROOT_HEART}),
    _room(ROOT_HEART, "Sleeping Heart", ROOT, "A continent-sized mycelial pulse can be felt through the floor. It does not seem aware of you, which is somehow reassuring.", {"up": ROOT_MEMORY}),

    _room(RED_ROAD, "Red Country Road", RED, "A straight black road crosses red grass beneath a pale blue sky. White roadside lines use measurements no Human remembers.", {"east": RED_STATION}),
    _room(RED_STATION, "Service Station", RED, "Glass doors reveal shelves of colorful packages printed in almost-readable Earth lettering. The lights buzz without wires.", {"west": RED_ROAD, "east": RED_HOUSES}),
    _room(RED_HOUSES, "Identical Houses", RED, "A neighborhood repeats the same pale house farther than perspective allows. Every mailbox bears your character's surname, whether you have one or not.", {"west": RED_STATION, "north": RED_TOWER}),
    _room(RED_TOWER, "Water Tower", RED, "A red-painted water tower rises over the false suburb. A small red key has been taped beneath the lowest ladder rung.", {"south": RED_HOUSES}),

    _room(SEA_BEACH, "Dry Beach Beneath the Sea", SEA, "White sand lies dry under an ocean suspended miles overhead. Fish cast moving shadows over your boots.", {"east": SEA_PIER}),
    _room(SEA_PIER, "Upward Pier", SEA, "A wooden pier climbs vertically toward the ocean above. Barnacles grow on its upper surfaces where no water reaches.", {"west": SEA_BEACH, "up": SEA_WRECK}),
    _room(SEA_WRECK, "Hanging Wreck", SEA, "A ship hangs upside down from the sea surface, sails drifting through blue water while its keel points toward you.", {"down": SEA_PIER, "east": SEA_LIGHT}),
    _room(SEA_LIGHT, "Inverted Lighthouse", SEA, "The lighthouse hangs from an island above. Its beam shines downward through air, illuminating things that vanish when directly observed.", {"west": SEA_WRECK}),

    _room(DOOR_FIELD, "White Field", DOOR, "You step from a red door standing alone in a field of white grass. There is no sun, but everything has a shadow.", {"east": DOOR_VILLAGE}),
    _room(DOOR_VILLAGE, "Closed Village", DOOR, "Every house is carefully maintained and completely closed. Fresh bread cools behind one window. No chimney smokes.", {"west": DOOR_FIELD, "north": DOOR_HALL}),
    _room(DOOR_HALL, "Long Hall", DOOR, "A public hall contains portraits of people who have not yet been born in Astralis. Several frames are empty.", {"south": DOOR_VILLAGE, "east": DOOR_RED}),
    _room(DOOR_RED, "The Other Red Door", DOOR, "Another red door stands in the final wall. Its keyhole is on the wrong side.", {"west": DOOR_HALL}),

    _room(UNSPOKEN_EDGE, "An Edge Without Direction", UNSPOKEN, "There is no useful sky, floor or horizon. Distance begins only when you stop trying to measure it.", {"forward": UNSPOKEN_DISTANCE}),
    _room(UNSPOKEN_DISTANCE, "The Distance", UNSPOKEN, "Something like landscape occurs very far away and remains equally far away after walking toward it.", {"back": UNSPOKEN_EDGE, "forward": UNSPOKEN_MOUTH}),
    _room(UNSPOKEN_MOUTH, "Closed Mouth", UNSPOKEN, "A shape resembling a closed mouth occupies more space than the room containing it. It does not breathe.", {"back": UNSPOKEN_DISTANCE, "forward": UNSPOKEN_LAST}),
    _room(UNSPOKEN_LAST, "The Last Place", UNSPOKEN, "Here the echo of the First Breath is absent. The absence is not silence. It is the first thing you have found that the echo does not reach.", {"back": UNSPOKEN_MOUTH}),
)

ITEMS = (
    ItemDefinition("pale_unwritten_letter", "Unwritten Letter", "A sealed letter whose paper becomes covered in handwriting only when nobody is reading it.", "trophy", tier=4),
    ItemDefinition("pale_second_shadow", "Folded Second Shadow", "A strip of gray cloth that casts a second, slightly delayed shadow.", "fashion", tier=4),
    ItemDefinition("pale_bell_dust", "Bell Dust", "Fine bronze dust collected beneath a bell that never visibly moves.", "material", tier=4),
    ItemDefinition("brass_heaven_hand", "Small Brass Hand", "A clockwork pointing hand that rotates toward large machinery when left on a table.", "trophy", tier=4),
    ItemDefinition("brass_heaven_seedgear", "Seed Gear", "A gear with teeth too fine for any Astralis tool to cut.", "material", tier=4),
    ItemDefinition("brass_heaven_ready_badge", "READY Badge", "A heavy brass badge stamped READY in a script older than Veyra's machine culture.", "fashion", tier=4),
    ItemDefinition("root_below_memory_spore", "Memory Spore", "A dark pearl-like spore containing a sensory memory from before any known Sporekin lineage.", "trophy", tier=4),
    ItemDefinition("root_below_heartfiber", "Heartfiber", "Warm fungal fiber shed from something immeasurably old beneath the Root Below.", "material", tier=4),
    ItemDefinition("root_below_crown", "Crown of Quiet Caps", "Tiny pale caps grow from a living circlet and never join a visible Chorus.", "fashion", tier=4),
    ItemDefinition("red_country_key", "Small Red Key", "A simple red-painted key recovered from a country that should not resemble Earth.", "trophy", tier=4),
    ItemDefinition("red_country_receipt", "Receipt From Nowhere", "A faded paper receipt denominated in a currency Humans no longer recognize.", "trophy", tier=4),
    ItemDefinition("red_country_soda_tab", "Red Aluminum Tab", "A pull-tab of impossibly light red metal, useless and intensely collectible.", "trophy", tier=4),
    ItemDefinition("sea_above_sky_salt", "Sky Salt", "Blue-white salt gathered from dry sand beneath an upside-down ocean.", "material", tier=4),
    ItemDefinition("sea_above_downward_pearl", "Downward Pearl", "A pearl whose highlight remains on its lower edge regardless of the light source.", "trophy", tier=4),
    ItemDefinition("sea_above_sailcloth", "Falling Sailcloth", "A strip of sail that always hangs toward the nearest large body of water instead of toward the ground.", "fashion", tier=4),
    ItemDefinition("behind_door_blank_portrait", "Blank Future Portrait", "An ornate miniature portrait frame. The painted figure has not appeared yet.", "trophy", tier=5),
    ItemDefinition("behind_door_white_grass", "White Grass Braid", "A braid of white grass that casts a shadow in total darkness.", "fashion", tier=5),
    ItemDefinition("behind_door_wrong_keyhole", "Wrong-Sided Keyplate", "A red enamel keyplate whose mechanism can only be operated from the side without a keyhole.", "trophy", tier=5),
    ItemDefinition("unspoken_absence", "A Measured Absence", "The inventory insists this is an object. Looking directly at it supplies no useful description.", "trophy", tier=5),
    ItemDefinition("unspoken_closed_word", "Closed Word", "A black mark on no visible surface. You remember possessing it more clearly than you can see it.", "trophy", tier=5),
    ItemDefinition("unspoken_no_echo", "No-Echo Fragment", "A smooth fragment around which ambient sound behaves normally, except that nothing ever reverberates.", "trophy", tier=5),
)

PLANE_DISCOVERY_FLAGS = {plane.key: f"planar_discovered_{plane.key}" for plane in PLANES}


def _register_content(world_service) -> None:
    for item in ITEMS:
        if item.key not in crafting.ITEMS_BY_KEY:
            crafting.register_item(item)
    for room in ROOMS:
        legacy_world.ROOMS_BY_KEY[room.key] = room
        if not any(existing.key == room.key for existing in legacy_world.ROOMS):
            legacy_world.ROOMS = legacy_world.ROOMS + (room,)
        world_service.legacy_rooms[room.key] = room
    cache = getattr(world_service, "_scene_cache", None)
    if cache is not None:
        for room in ROOMS:
            cache.pop(room.key, None)


def _has(session, flag: str) -> bool:
    return bool(session.character and flag in session.database.list_flags(session.character.id))


def _item(session, key: str) -> int:
    return 0 if session.character is None else session.database.item_quantity(session.character.id, key)


def _move(session, destination: str) -> None:
    session.database.set_character_room(session.character.id, destination)
    session.character = replace(session.character, current_room=destination)


def _discover(session, plane: PlaneDefinition) -> None:
    flag = PLANE_DISCOVERY_FLAGS[plane.key]
    if _has(session, flag):
        return
    session.database.grant_flag(session.character.id, flag)
    if plane.chronicle_public:
        _chronicle_insert(
            session.database,
            event_key=f"planar_first:{plane.key}",
            day=ASTRALIS_CLOCK.now().day_number,
            category="discovery",
            text=f"{session.character.name} returned with the first credible account of {plane.name}.",
            character_id=session.character.id,
            character_name=session.character.name,
        )


def _planes_seen(session) -> int:
    flags = session.database.list_flags(session.character.id)
    return sum(1 for value in PLANE_DISCOVERY_FLAGS.values() if value in flags)


async def _enter(session, plane: PlaneDefinition, room: str, text: str) -> None:
    _move(session, room)
    _discover(session, plane)
    await session.send(text + "\r\n")
    await session.look()


async def _return(session, room: str, text: str) -> None:
    _move(session, room)
    await session.send(text + "\r\n")
    await session.look()


def install_planar_realms_runtime(player_session_class, world_service) -> None:
    if getattr(player_session_class, "_planar_realms_installed", False):
        return
    _register_content(world_service)
    original_prompt = player_session_class.playing_prompt

    async def playing_prompt(self):
        command = await self.prompt("\r\n> ")
        if command is None:
            from mud.session import SessionState
            self.state = SessionState.DISCONNECTED
            return
        verb = " ".join(command.strip().lower().split())
        room = self.character.current_room if self.character else ""

        # Entrances are deliberately contextual and absent from any global plane checklist.
        if room == GRAVEWATCH_CRYPT_KEY and verb == "listen between bells":
            if not _has(self, GRAVEWATCH_CASTELLAN_DEFEATED_FLAG):
                await self.send("There is only the ordinary dead quiet of the crypt.\r\n")
                return
            return await _enter(self, PLANES[0], PALE_SHORE, "For one instant two silences overlap. You step through the thinner one.")

        if room == UNDERCLOCK_MINUTE_KEY and verb == "touch zero":
            if not _has(self, UNDERCLOCK_COMPLETE_FLAG):
                await self.send("The zero mark is merely cold brass. The machine has not yet shown you enough of itself.\r\n")
                return
            return await _enter(self, PLANES[1], BRASS_GATE, "The zero on the gauge opens like an iris. Beyond it waits a city of stopped machinery.")

        if room == SABLEWATER_DRIFTWOOD_SHRINE_KEY and verb in {"kneel at roots", "kneel roots"}:
            if self.character.level < 7:
                await self.send("The roots feel old, wet, and entirely local.\r\n")
                return
            return await _enter(self, PLANES[2], ROOT_MOUTH, "The shrine root flexes under your hand and becomes far larger than the tree that owns it.")

        if room == WAYMEET_BROKEN_MILE_KEY and verb in {"strike dead lighter", "strike lighter"}:
            if _item(self, "dead_earth_lighter") <= 0 and _item(self, "human_blue_plastic_card") <= 0:
                await self.send("You have nothing here that remembers Earth strongly enough to answer.\r\n")
                return
            return await _enter(self, PLANES[3], RED_ROAD, "The lighter sparks without fuel. For a fraction of a second the road smells like hot asphalt, and then you are standing on it.")

        if room == SABLEWATER_ROOKERY_KEY and verb in {"look into sky pool", "look into sky-pool"}:
            moment = ASTRALIS_CLOCK.now()
            if moment.moon_phase != "full" or moment.phase != "night":
                await self.send("The rainwater reflects an ordinary Astralis sky.\r\n")
                return
            return await _enter(self, PLANES[4], SEA_BEACH, "The reflection deepens until the stars become fish. You fall upward without moving.")

        if room == VEYRA_KEYHOUSE_KEY and verb == "try red key":
            if _item(self, "red_country_key") <= 0 and _item(self, "veyra_red_door_key") <= 0:
                await self.send("None of the keys you carry make the unnumbered red seam in the rear wall acknowledge you.\r\n")
                return
            return await _enter(self, PLANES[5], DOOR_FIELD, "A red seam appears in the Keyhouse wall. The key turns before you touch the lock.")

        if room == ECHO_FIRST_BREATH_MARGIN and verb == "wait for second word":
            moment = ASTRALIS_CLOCK.now()
            if not _has(self, ECHO_COMPLETE) or _planes_seen(self) < 5 or moment.day_number % 17 != 3:
                await self.send("Nothing follows the First Breath. Perhaps that is the answer.\r\n")
                return
            return await _enter(self, PLANES[6], UNSPOKEN_EDGE, "You wait long enough that silence stops being the correct word for what surrounds you.")

        # Rare plane-specific discoveries. Each is one-time per character; several are intentionally mundane.
        rewards = {
            (PALE_HOUSE, "search table"): ("pale_unwritten_letter", "Among the abandoned things is a sealed Unwritten Letter."),
            (PALE_BELL, "touch dust"): ("pale_bell_dust", "Bronze powder gathers on your fingertips: Bell Dust."),
            (BRASS_THRONE, "take hand"): ("brass_heaven_hand", "The smallest pointing hand releases from the throne and settles in your palm."),
            (BRASS_ORRERY, "search gears"): ("brass_heaven_seedgear", "One tiny Seed Gear lies beneath a mechanical tree."),
            (ROOT_MEMORY, "touch loam"): ("root_below_memory_spore", "The loam yields a black Memory Spore containing a sensation older than language."),
            (ROOT_HEART, "gather fiber"): ("root_below_heartfiber", "A loose strand separates from the sleeping mass without waking it: Heartfiber."),
            (RED_TOWER, "search ladder"): ("red_country_key", "Tape peels from the lowest rung. Beneath it is a Small Red Key."),
            (RED_STATION, "search counter"): ("red_country_receipt", "Behind the counter you find a Receipt From Nowhere."),
            (SEA_BEACH, "gather salt"): ("sea_above_sky_salt", "You collect blue-white Sky Salt from a line the upside-down tide never reaches."),
            (SEA_WRECK, "search wreck"): ("sea_above_downward_pearl", "Inside an inverted locker rests a Downward Pearl."),
            (DOOR_HALL, "take portrait"): ("behind_door_blank_portrait", "One empty frame comes free. Its plaque is warm but still blank."),
            (DOOR_FIELD, "braid grass"): ("behind_door_white_grass", "You braid three strands of white grass. Their shadow remains after you close your hand."),
            (UNSPOKEN_MOUTH, "measure absence"): ("unspoken_absence", "You perform an action you will later remember as measuring. Something is now in your inventory."),
            (UNSPOKEN_LAST, "listen for echo"): ("unspoken_no_echo", "Nothing returns your listening. A smooth fragment is present when you lower your hand."),
        }
        reward = rewards.get((room, verb))
        if reward is not None:
            item_key, text = reward
            flag = f"planar_reward:{item_key}"
            if _has(self, flag):
                await self.send("Whatever was here for you has already been taken.\r\n")
                return
            self.database.grant_flag(self.character.id, flag)
            self.database.add_item(self.character.id, item_key, 1)
            await self.send(text + "\r\n")
            return

        # Plane-specific story actions reveal lore without creating quest journals.
        story = {
            (PALE_STREET, "listen"): "You hear conversations ending, doors closing, footsteps choosing roads not taken. None begin.",
            (BRASS_AVENUE, "read gauges"): "Every machine says READY. None say what they were ready to do.",
            (ROOT_MEMORY, "listen"): "The Sporekin Chorus is present only as a distant descendant. Something here remembers before it.",
            (RED_HOUSES, "read mailboxes"): "Every mailbox uses a naming convention that feels Human and wrong. One bears your name in lettering faded by decades.",
            (SEA_LIGHT, "watch beam"): "The beam briefly outlines a city suspended between you and the sea. When you look directly at it, there is only air.",
            (DOOR_VILLAGE, "knock"): "Someone inside knocks back once. The door never opens.",
            (UNSPOKEN_LAST, "listen"): "There is no echo here. Not a quiet echo. None. For the first time, the First Breath appears to have a boundary.",
        }.get((room, verb))
        if story:
            await self.send(story + "\r\n")
            return

        if room in PLANE_BY_ROOM and verb in {"return", "return astralis", "go home"}:
            plane = PLANE_BY_ROOM[room]
            return_room = {
                PALE: GRAVEWATCH_CRYPT_KEY,
                BRASS: UNDERCLOCK_MINUTE_KEY,
                ROOT: SABLEWATER_DRIFTWOOD_SHRINE_KEY,
                RED: WAYMEET_BROKEN_MILE_KEY,
                SEA: SABLEWATER_ROOKERY_KEY,
                DOOR: VEYRA_KEYHOUSE_KEY,
                UNSPOKEN: ECHO_FIRST_BREATH_MARGIN,
            }[plane.key]
            return await _return(self, return_room, "The foreign geometry releases you. Astralis feels unusually heavy and ordinary.")

        async def one_shot_prompt(_text=""):
            return command
        previous = self.prompt
        self.prompt = one_shot_prompt
        try:
            return await original_prompt(self)
        finally:
            self.prompt = previous

    player_session_class.playing_prompt = playing_prompt
    player_session_class._planar_realms_installed = True
