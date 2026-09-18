from __future__ import annotations

import hashlib
from dataclasses import dataclass

import mud.actor_inspection as actor_inspection
import mud.combat as combat
import mud.crafting as crafting
import mud.living_world as living
from mud.combat import EnemyDefinition
from mud.world import ROOMS_BY_KEY

LIVING_WORLD_VARIETY_VERSION = "2.1.0"
BASE_PULSES = tuple(living.PULSE_TEMPLATES)

@dataclass(frozen=True, slots=True)
class RegionSpec:
    region_key: str
    name: str
    enemy_key: str
    enemy_name: str
    enemy_description: str
    hp: int
    ac: int
    damage: int
    xp: int
    resource_nodes: tuple[str, ...]
    sender: str

@dataclass(frozen=True, slots=True)
class EventMeta:
    region_key: str
    region_name: str
    actor_name: str = ""
    actor_description: str = ""
    aliases: tuple[str, ...] = ()
    scene_name: str = ""
    scene_details: tuple[str, ...] = ()

REGIONS = (
    RegionSpec("junk_city_and_swamps", "Junk City and the Rattlefen", "living_scrapback_varmint", "Scrapback Varmint", "a wire-and-shell swamp scavenger bold enough to charge when cornered", 38, 5, 4, 28, ("greenleaf_patch", "bitterroot_cluster", "cotton_patch", "lavender_patch", "iron_vein"), "Vikka Three-Nails, Clattergate Claim Desk"),
    RegionSpec("waymeet_frontier", "Waymeet", "living_mirehorn_stray", "Mirehorn Stray", "a mud-dark antlered grazer driven too close to the road", 62, 8, 7, 48, ("lavender_patch", "greenleaf_patch", "iron_vein", "coal_seam", "cotton_patch"), "Mara Pell, Waymeet Road Post"),
    RegionSpec("veyra_city", "Veyra", "living_roofjackal", "Roofjackal", "a long-legged city scavenger driven down from the roofs by bells and market scraps", 92, 11, 9, 72, ("lavender_patch", "cotton_patch", "greenleaf_patch", "bitterroot_cluster", "coal_seam"), "Pikka Ninepins, Veyra Exchange"),
    RegionSpec("greywake_march", "Greywake March", "living_bellhide_runner", "Bellhide Runner", "a rangy grey grazer with a cracked harness-bell caught around one horn", 78, 10, 8, 60, ("bitterroot_cluster", "greenleaf_patch", "wool_flock", "iron_vein", "lavender_patch"), "Oryn Vale, Greywake Warden Post"),
    RegionSpec("sablewater_reach", "Sablewater Reach", "living_floodjaw_scavenger", "Floodjaw Scavenger", "a long-backed floodplain predator nosing through ferry refuse", 86, 11, 9, 68, ("bitterroot_cluster", "greenleaf_patch", "cotton_patch", "lavender_patch", "iron_vein"), "Jessa Pike, Sablewater Ferry Ledger"),
    RegionSpec("broken_reach", "Broken Reach", "living_reedglass_prowler", "Reedglass Prowler", "a lean road predator with glassy reeds caught through its dark coat", 128, 13, 12, 104, ("bitterroot_cluster", "greenleaf_patch", "cobalt_vein", "silk_cocoon_cluster", "iron_vein"), "Hesta Vane, Reach Survey Post"),
    RegionSpec("salt_kingdoms_whitewake", "Salt Kingdoms", "living_saltback_lurker", "Saltback Lurker", "a pale basin hunter crusted with dry salt and nearly invisible against old stone", 205, 16, 17, 176, ("cobalt_vein", "silk_cocoon_cluster", "iron_vein", "giant_spider_nest", "moonsilver_vein"), "Tavi Saltmark, Keelspire Basin Post"),
    RegionSpec("crownfire_march", "Crownfire March", "living_banner_scavenger", "Banner Scavenger", "a heavy carrion beast that has learned camps mean food and distracted people", 300, 19, 23, 255, ("ghostmoss_patch", "emberite_vein", "cobalt_vein", "bitterroot_cluster", "lavender_patch"), "Nera Ashfoot, Marchward Dispatch"),
)
REGIONS_BY_KEY = {r.region_key: r for r in REGIONS}

RACE_WRITERS = {
    "human": "Blackwall Road Desk", "forest_elf": "Len of the Greenway Keepers",
    "moon_elf": "Third Chair Correspondence, High Horizon", "dwarf": "Orra Coilmark, Freight Registry",
    "goblin": "Vikka Three-Nails, Forwarded Claims", "troll": "Raska, Frostroot Trail Word",
    "undead": "Keeper Ses, Necropolis Quiet Post", "sporekin": "Memory-Keeper Nema, Lumen Hollow",
}
OPENERS = (
    "You were away for {days} Astralis {day_word}. The roads kept moving.",
    "The post book marks you away for {days} Astralis {day_word}; one current notice looked worth forwarding.",
    "While you were away for {days} Astralis {day_word}, small things kept changing outside the gate.",
    "You missed {days} Astralis {day_word} of ordinary road noise. Here is the part still current.",
    "After {days} Astralis {day_word} away, this is the one fresh report still pinned up.",
    "The world had {days} Astralis {day_word} to rearrange itself while you were gone. One change is still visible.",
)
CLOSERS = (
    "That is the current word from the road.",
    "By tomorrow the road will probably have found something else to talk about.",
    "The rest of the post book is mud, prices, and arguments too ordinary to copy here.",
    "That is all the desk has worth forwarding today.",
    "Someone else will have changed the story by sundown.",
    "If you pass that way, you can decide for yourself how much of the rumor was true.",
)
SUBJECTS = (
    "Road note — Day {day}", "Dispatch from {region} — Day {day}", "Something changed near {room} — Day {day}",
    "Today's useful rumor — Day {day}", "A note from {region} — Day {day}", "Field post: {room} — Day {day}",
    "What changed while you were out — Day {day}", "One thing worth knowing — Day {day}",
)
MERCHANT_NAMES = ("Nell Brasscup", "Orvo Six-Pegs", "Miri Vale", "Hask Threadbare", "Pella Cindercart", "Senn Underbridge", "Toma Reedhook", "Ilyr Quickchalk", "Bessa Turnwheel", "Corin Smallchange", "Vella Ashcart", "Dorrin Two-Ledgers")
MERCHANT_MOTIFS = (
    ("surplus", "{actor} has opened a temporary surplus table at {room}."),
    ("repair", "{actor}'s repair cart has stopped at {room} for the day."),
    ("mixed_lot", "{actor} is breaking up a mixed trade lot at {room}."),
    ("weatherbound", "Bad weather has stranded {actor} at {room}, and the cargo is being sold instead of hauled farther."),
    ("shared_wagon", "A shared freight wagon run by {actor} is unloading at {room}."),
    ("oddments", "{actor} is trading road oddments from a blanket at {room}."),
)
THREAT_MOTIFS = (
    ("tracks", "Fresh tracks around {room} belong to a {enemy} that has stopped avoiding the road."),
    ("packs", "A {enemy} has been tearing into unattended packs near {room}."),
    ("night", "Night workers at {room} finally identified the thing making the noise: a {enemy}."),
    ("route", "A territorial {enemy} is making one corner of {room} unpleasant to use."),
    ("scraps", "A {enemy} has learned that {room} produces easy scraps."),
)
STORY_MOTIFS = (
    ("repair", "repair scene", "A repair crew at {room} is solving one small problem with methods borrowed from three cultures."),
    ("argument", "public argument", "Two respected locals at {room} are disagreeing loudly enough that strangers have started taking sides."),
    ("music", "street performance", "An improvised performance at {room} keeps gaining musicians who were not part of the plan."),
    ("meal", "shared meal", "A cooking fire at {room} has become an accidental shared meal for whoever happens to be passing."),
    ("animals", "animal commotion", "A harmless animal commotion at {room} has stopped traffic more effectively than an official sign."),
    ("game", "public game", "Workers at {room} have turned a slow hour into a fiercely disputed local game."),
    ("delivery", "misdelivered cargo", "A badly labeled delivery at {room} is being identified one item and one opinion at a time."),
    ("weather", "weather spectacle", "A brief turn in the weather has made {room} look strange enough that people keep stopping to stare."),
    ("craft", "craft demonstration", "A craftsperson at {room} is doing ordinary work so skillfully that a small audience has formed."),
    ("story", "roadside story", "Someone at {room} is telling a story that every listener insists they heard differently the first time."),
)
SCENE_DETAILS = (
    "Nobody organized this; it became a gathering because people kept stopping.",
    "Bystanders offer help, advice, and contradictory eyewitness versions of what started it.",
    "People have shifted crates and stools aside to make room without ever agreeing that a crowd has formed.",
    "Someone who was only passing through has already become part of the story.",
    "The little crowd changes every few minutes, but the event itself keeps going.",
)
WARE_POOLS = (
    (("iron_ore", 1), ("raw_cotton", 1), ("greenleaf", 1)),
    (("coal", 1), ("cotton_thread", 1), ("lavender_blossom", 1)),
    (("bitterroot", 1), ("raw_wool", 1), ("iron_ore", 1)),
    (("cobalt_ore", 1), ("silk_cocoons", 1), ("coal", 1)),
    (("moonsilver_ore", 1), ("lavender_blossom", 1), ("greenleaf", 1)),
    (("emberite_ore", 1), ("raw_wool", 1), ("bitterroot", 1)),
)
EVENT_META_BY_KEY: dict[str, EventMeta] = {}
GENERATED_PULSES: tuple[living.DailyPulse, ...] = ()
ALL_PULSES = BASE_PULSES


def _stable_index(seed: str, size: int) -> int:
    return int.from_bytes(hashlib.sha256(seed.encode()).digest()[:8], "big") % size


def _rooms_for(region_key: str) -> tuple[tuple[str, str], ...]:
    rooms = tuple(sorted((k, r.name) for k, r in ROOMS_BY_KEY.items() if r.region_key == region_key))
    if not rooms:
        raise RuntimeError(f"Living-world variety region has no rooms: {region_key}")
    return rooms


def _register_threats() -> None:
    additions = []
    for r in REGIONS:
        if r.enemy_key in combat.ENEMIES_BY_KEY:
            continue
        d = EnemyDefinition(r.enemy_key, r.enemy_name, tuple(dict.fromkeys((r.enemy_name.lower(), *r.enemy_name.lower().split()))), r.enemy_description, r.hp, r.ac, r.damage, 3.0, r.xp, retaliates=True)
        combat.ENEMIES_BY_KEY[d.key] = d
        additions.append(d)
    if additions:
        combat.ENEMIES = combat.ENEMIES + tuple(additions)


def _build_catalog() -> tuple[living.DailyPulse, ...]:
    pulses, meta = [], {}
    for ri, r in enumerate(REGIONS):
        rooms = _rooms_for(r.region_key)
        for i, (motif, headline) in enumerate(MERCHANT_MOTIFS):
            rk, rn = rooms[(i * 2 + ri) % len(rooms)]; actor = MERCHANT_NAMES[(ri * 3 + i) % len(MERCHANT_NAMES)]; key = f"variety:{r.region_key}:merchant:{motif}:{i}"
            pulses.append(living.DailyPulse(key, "merchant", headline.format(actor=actor, room=rn), "The stall is carrying ordinary road materials that usually require a longer trip to find.", f"'{actor} says the rarest thing on the table is convenience.'", rk, rn, "BROWSE WANDERER", merchant_wares=WARE_POOLS[(ri + i) % len(WARE_POOLS)]))
            meta[key] = EventMeta(r.region_key, r.name, actor, f"a temporary road trader working a compact stall at {rn}", ("wanderer", "peddler", "trader", actor.split()[0].lower()))
        for i, node_key in enumerate(r.resource_nodes):
            if node_key not in crafting.RESOURCE_NODES_BY_KEY:
                raise RuntimeError(f"Unknown living-world resource node: {node_key}")
            rk, rn = rooms[(i * 3 + 1) % len(rooms)]; node = crafting.RESOURCE_NODES_BY_KEY[node_key]; key = f"variety:{r.region_key}:resource:{node_key}:{i}"
            pulses.append(living.DailyPulse(key, "resource", f"A fresh {node.name.lower()} find has opened near {rn}.", f"Fresh ground has exposed a small {node.name.lower()} source, and gatherers have already started working the edge of it.", f"'People around {rn} are suddenly carrying baskets and pretending that was always the plan.'", rk, rn, "RESOURCES", resource_node=node_key))
            meta[key] = EventMeta(r.region_key, r.name, scene_name=node.name, scene_details=(f"Freshly exposed {node.name.lower()} is visible along the disturbed ground.", "Basket marks, cut stems, and fresh footprints show that local gatherers have already found it."))
        for i, (motif, headline) in enumerate(THREAT_MOTIFS):
            rk, rn = rooms[(i * 2 + 2) % len(rooms)]; key = f"variety:{r.region_key}:threat:{motif}:{i}"
            pulses.append(living.DailyPulse(key, "threat", headline.format(room=rn, enemy=r.enemy_name), f"Fresh sign points to one {r.enemy_name}, and the tracks are recent enough that road workers are still avoiding the area.", f"'One {r.enemy_name.lower()}, one bad habit, and plenty of volunteers for somebody else to handle it.'", rk, rn, "HUNT DISTURBANCE", threat_key=r.enemy_key))
            meta[key] = EventMeta(r.region_key, r.name, scene_name=r.enemy_name, scene_details=(f"Fresh tracks around {rn} match a {r.enemy_name}.", "Broken brush and churned mud show where it left the road only a short while ago."))
        for i, (motif, scene, headline) in enumerate(STORY_MOTIFS):
            rk, rn = rooms[(i * 3 + 3) % len(rooms)]; key = f"variety:{r.region_key}:story:{motif}:{i}"; details = tuple(SCENE_DETAILS[(i + ri + j) % len(SCENE_DETAILS)] for j in range(3))
            pulses.append(living.DailyPulse(key, "story", headline.format(room=rn), f"People at {rn} are still talking over one another about it, and the small crowd has not dispersed yet.", f"'Something small is happening at {rn}, so everyone already has a different version of it.'", rk, rn, "OBSERVE SCENE"))
            meta[key] = EventMeta(r.region_key, r.name, scene_name=scene, scene_details=details)
    EVENT_META_BY_KEY.clear(); EVENT_META_BY_KEY.update(meta)
    return tuple(pulses)


def pulse_for_day(day_number: int) -> living.DailyPulse:
    day = max(1, int(day_number)); slot = (day - 1) % 97
    if slot < len(BASE_PULSES): return BASE_PULSES[slot]
    if not GENERATED_PULSES: return BASE_PULSES[_stable_index(f"fallback:{day}", len(BASE_PULSES))]
    return GENERATED_PULSES[_stable_index(f"dreams-living-world-v2:{day}", len(GENERATED_PULSES))]


def _meta_for(pulse: living.DailyPulse) -> EventMeta:
    if pulse.key in EVENT_META_BY_KEY: return EVENT_META_BY_KEY[pulse.key]
    room = ROOMS_BY_KEY.get(pulse.room_key); region_key = room.region_key if room else "waymeet_frontier"; r = REGIONS_BY_KEY.get(region_key, REGIONS_BY_KEY["waymeet_frontier"])
    return EventMeta(r.region_key, r.name)


def create_return_letter(session, from_day: int, to_day: int) -> bool:
    c = getattr(session, "character", None)
    if c is None or to_day <= from_day: return False
    pulse = pulse_for_day(to_day); meta = _meta_for(pulse); region = REGIONS_BY_KEY.get(meta.region_key, REGIONS_BY_KEY["waymeet_frontier"]); days = to_day - from_day
    opener = OPENERS[_stable_index(f"opener:{c.id}:{to_day}:{pulse.key}", len(OPENERS))].format(days=days, day_word="day" if days == 1 else "days")
    race_sender = RACE_WRITERS.get(c.race or ""); sender = race_sender if race_sender and _stable_index(f"voice:{c.id}:{to_day}:{pulse.key}", 3) == 0 else region.sender
    subject = SUBJECTS[_stable_index(f"subject:{c.id}:{to_day}:{pulse.key}", len(SUBJECTS))].format(day=to_day, region=meta.region_name, room=pulse.room_name)
    action = f" If you pass that way, stop at {pulse.room_name} and {pulse.command_hint}." if pulse.command_hint else ""
    past = list(range(from_day + 1, to_day))
    if len(past) > 2:
        a = past[_stable_index(f"past-a:{c.id}:{to_day}", len(past))]; rest = [d for d in past if d != a]; past = sorted((a, rest[_stable_index(f"past-b:{c.id}:{to_day}", len(rest))]))
    history = " Older lines crossed out in the post book: " + " / ".join(pulse_for_day(d).headline for d in past) if past else ""
    closer = CLOSERS[_stable_index(f"closer:{c.id}:{to_day}:{pulse.key}", len(CLOSERS))]
    body = f"{opener} {pulse.headline} {pulse.summary}{action}{history} {closer}"
    with session.database.connect() as db:
        cursor = db.execute("INSERT OR IGNORE INTO living_mail (character_id, astralis_day, sender, subject, body) VALUES (?, ?, ?, ?, ?)", (c.id, int(to_day), sender, subject, body))
    return bool(cursor.rowcount)


def _visible_event_actor(session):
    c = getattr(session, "character", None)
    if c is None: return None
    pulse = pulse_for_day(living.ASTRALIS_CLOCK.now().day_number); meta = EVENT_META_BY_KEY.get(pulse.key)
    if pulse.kind != "merchant" or c.current_room != pulse.room_key or meta is None: return None
    return actor_inspection.VisibleActor(f"living_event_actor:{pulse.key}", meta.actor_name, meta.actor_description, "npc", meta.aliases)


def _patch_actor_visibility() -> None:
    if getattr(actor_inspection, "_living_world_variety_visibility_applied", False): return
    original = actor_inspection.visible_actors
    def visible_actors(session, world_service):
        actors = list(original(session, world_service)); extra = _visible_event_actor(session)
        if extra and extra.name.lower() not in {a.name.lower() for a in actors}: actors.append(extra)
        return tuple(actors)
    actor_inspection.visible_actors = visible_actors; actor_inspection._living_world_variety_visibility_applied = True


async def _observe_story(session, pulse, meta, day: int) -> None:
    first = not living._event_done(session, day, pulse.key)
    if first: living._mark_event_done(session, day, pulse)
    await session.send(f"\r\n--- {meta.scene_name.title()} ---\r\n")
    await session.send((pulse.summary if first else "You look over the same temporary scene again; it has not reset for you.") + "\r\n")
    if meta.scene_details:
        start = _stable_index(f"scene:{session.character.id}:{day}:{pulse.key}", len(meta.scene_details))
        for j in range(min(2, len(meta.scene_details))): await session.send(meta.scene_details[(start + j) % len(meta.scene_details)] + "\r\n")
    await session.send("Around you, the conversation keeps moving without waiting for anyone to declare the moment finished.\r\n")


async def _show_event(session, pulse) -> None:
    if session.character.current_room != pulse.room_key:
        await session.send(f"Today's world event is around {pulse.room_name}. DISPATCH gives the full notice.\r\n"); return
    await session.send(f"\r\n--- Happening Here Today ---\r\n{pulse.headline}\r\n{pulse.summary}\r\nTry: {pulse.command_hint}\r\n")


def apply_living_world_event_variety(player_session_class) -> None:
    global GENERATED_PULSES, ALL_PULSES
    if getattr(player_session_class, "_living_world_variety_runtime_applied", False): return
    _register_threats(); GENERATED_PULSES = _build_catalog(); ALL_PULSES = BASE_PULSES + GENERATED_PULSES
    living.PULSE_TEMPLATES = ALL_PULSES; living.pulse_for_day = pulse_for_day; living._create_return_letter = create_return_letter; _patch_actor_visibility()
    previous = player_session_class.playing_prompt
    async def playing_prompt(self) -> None:
        c = getattr(self, "character", None)
        if c is None: await previous(self); return
        command = await self.prompt("\r\n> ")
        if command is None:
            state = getattr(self, "state", None)
            if state is not None and hasattr(type(state), "DISCONNECTED"): self.state = type(state).DISCONNECTED
            return
        stripped = command.strip(); normalized = " ".join(stripped.lower().split()); moment = living.ASTRALIS_CLOCK.now(); pulse = living._sync_resource_shift(moment); meta = _meta_for(pulse)
        if normalized in {"event", "world event", "local event", "happening today"}: await _show_event(self, pulse); return
        if c.current_room == pulse.room_key:
            if pulse.kind == "story" and normalized in {"observe scene", "investigate scene", "watch scene", "observe event", "investigate event"}: await _observe_story(self, pulse, meta, moment.day_number); return
            if pulse.kind == "merchant" and meta.actor_name and normalized.startswith(("look ", "look at ", "examine ", "talk ", "talk to ")):
                target = normalized.split(" ", 1)[1]
                if target in {"wanderer", "peddler", "trader", meta.actor_name.lower(), meta.actor_name.split()[0].lower()}:
                    await self.send(f"\r\n{meta.actor_name} — {meta.actor_description}.\r\n{pulse.summary}\r\nUse BROWSE WANDERER to see today's stock.\r\n"); return
            if pulse.kind in {"resource", "threat"} and normalized in {"look event", "examine event", "look disturbance", "examine disturbance"}: await _show_event(self, pulse); return
        had_prompt = "prompt" in self.__dict__; old_prompt = self.__dict__.get("prompt")
        async def replay(_text: str): return command
        self.prompt = replay
        try: await previous(self)
        finally:
            if had_prompt: self.prompt = old_prompt
            else: self.__dict__.pop("prompt", None)
    player_session_class.playing_prompt = playing_prompt; player_session_class._living_world_variety_runtime_applied = True
