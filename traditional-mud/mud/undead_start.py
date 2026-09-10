from __future__ import annotations

from dataclasses import replace

import mud.character_options as character_options
import mud.combat as combat
import mud.crafting as crafting
import mud.quests as quests
import mud.world as legacy_world
from mud.combat import EnemyDefinition, EnemyState
from mud.crafting import ItemDefinition
from mud.quests import QuestDefinition
from mud.room_engine import DescriptionLayer, ExitDefinition, FeatureDefinition, RoomAugmentation, ViewCondition
from mud.world import NpcDefinition, RoomDefinition


UNDEAD_REGION_KEY = "desert_necropolis"
UNDEAD_START_ROOM_KEY = "undead_reclamation_vault"
UNDEAD_SEVERANCE_HALL_KEY = "undead_severance_hall"
UNDEAD_CONCOURSE_KEY = "undead_necropolis_concourse"
UNDEAD_FORMER_LIVES_ARCHIVE_KEY = "undead_former_lives_archive"
UNDEAD_CHISEL_MARKET_KEY = "undead_chisel_market"
UNDEAD_COMMAND_VAULT_KEY = "undead_dead_command_vault"
UNDEAD_FREEHANDS_COURT_KEY = "undead_freehands_court"
UNDEAD_DESERT_GATE_KEY = "undead_desert_gate"
UNDEAD_SUNSCAR_ROAD_KEY = "undead_sunscar_road"

UNDEAD_START_ROOM_KEYS = (
    UNDEAD_START_ROOM_KEY,
    UNDEAD_SEVERANCE_HALL_KEY,
    UNDEAD_CONCOURSE_KEY,
    UNDEAD_FORMER_LIVES_ARCHIVE_KEY,
    UNDEAD_CHISEL_MARKET_KEY,
    UNDEAD_COMMAND_VAULT_KEY,
    UNDEAD_FREEHANDS_COURT_KEY,
    UNDEAD_DESERT_GATE_KEY,
    UNDEAD_SUNSCAR_ROAD_KEY,
)

UNDEAD_NO_VOICE_QUEST_KEY = "undead_no_voice_above_you"
UNDEAD_MEMORY_QUEST_KEY = "undead_what_was_yours"
UNDEAD_REMAINING_ORDER_QUEST_KEY = "undead_order_that_remains"
UNDEAD_CHOSEN_REQUEST_QUEST_KEY = "undead_request_not_order"

UNDEAD_OPENING_SEEN_FLAG = "undead_opening_seen"
UNDEAD_MASTER_SILENCE_HEARD_FLAG = "undead_master_silence_heard"
UNDEAD_RECLAIMER_HEARD_FLAG = "undead_reclaimer_heard"
UNDEAD_BINDING_EXAMINED_FLAG = "undead_binding_examined"
UNDEAD_ORDERS_SEVERED_FLAG = "undead_orders_severed"
UNDEAD_EFFECTS_EXAMINED_FLAG = "undead_former_effects_examined"
UNDEAD_MEMORY_SPARKED_FLAG = "undead_memory_sparked"
UNDEAD_MEMORY_KEEP_FLAG = "undead_memory_key_kept"
UNDEAD_MEMORY_DONATE_FLAG = "undead_memory_key_donated"
UNDEAD_MEMORY_DESTROY_FLAG = "undead_memory_key_destroyed"
UNDEAD_SENTINEL_DEFEATED_FLAG = "undead_bound_sentinel_defeated"
UNDEAD_COMMAND_SIGIL_BROKEN_FLAG = "undead_command_sigil_broken"
UNDEAD_MARKET_SEEN_FLAG = "undead_chisel_market_seen"
UNDEAD_REQUEST_HEARD_FLAG = "undead_freehand_request_heard"
UNDEAD_REQUEST_HELP_FLAG = "undead_request_helped"
UNDEAD_REQUEST_DECLINE_FLAG = "undead_request_declined"
UNDEAD_LAMP_DELIVERED_FLAG = "undead_lamp_glass_delivered"
UNDEAD_OPENING_COMPLETE_FLAG = "undead_opening_complete"
UNDEAD_FIRST_OUTSIDE_FLAG = "undead_first_outside_necropolis"

UNDEAD_MEMORY_KEY_ITEM = "undead_bent_brass_key"
UNDEAD_LAMP_GLASS_ITEM = "undead_shielded_lamp_glass"
UNDEAD_BOUND_SENTINEL_KEY = "undead_bound_ossuary_sentinel"

RECLAIMER_SEVRA_KEY = "undead_reclaimer_sevra"
KEEPER_ITH_KEY = "undead_severance_keeper_ith"
ARCHIVIST_MERA_KEY = "undead_archivist_mera"
BONEWRIGHT_KELL_KEY = "undead_bonewright_kell"
FREEHAND_TAL_KEY = "undead_freehand_tal"
GATE_TENDER_ORRA_KEY = "undead_gate_tender_orra"


UNDEAD_NO_VOICE_QUEST = QuestDefinition(
    key=UNDEAD_NO_VOICE_QUEST_KEY,
    name="No Voice Above You",
    style="structured",
    description=(
        "You wake in the Necropolis Reclamation Vault with no necromancer's command in your mind. "
        "Before the free Undead consider a newly recovered skeleton safe to join civic life, any surviving command magic must be found and severed."
    ),
    objective_steps=(
        ("listen_silence", "LISTEN for the voice or command that once directed your body."),
        ("talk_reclaimer", "TALK RECLAIMER in the Reclamation Vault."),
        ("inspect_binding", "Go EAST into the Hall of Severed Orders and EXAMINE BINDING."),
        ("sever_orders", "SEVER ORDERS at the severance frame."),
        ("complete", "No surviving master has authority over your body."),
    ),
)

UNDEAD_MEMORY_QUEST = QuestDefinition(
    key=UNDEAD_MEMORY_QUEST_KEY,
    name="What Was Yours",
    style="structured",
    description=(
        "The Necropolis keeps objects recovered with newly freed dead, but it does not decide whether a former life must be preserved. "
        "You are invited to face one ordinary fragment of memory and decide what, if anything, you want from it."
    ),
    objective_steps=(
        ("reach_archive", "Go SOUTH to the Necropolis Concourse, then WEST into the Former Lives Archive."),
        ("examine_effects", "EXAMINE EFFECTS laid out from your recovery bundle."),
        ("touch_key", "TOUCH KEY and see whether the ordinary object stirs anything."),
        ("choose_memory", "Choose what happens to it: KEEP KEY, DONATE KEY, or DESTROY KEY."),
        ("complete", "You decided for yourself what claim a former-life object has on your present identity."),
    ),
)

UNDEAD_REMAINING_ORDER_QUEST = QuestDefinition(
    key=UNDEAD_REMAINING_ORDER_QUEST_KEY,
    name="The Order That Remains",
    style="structured",
    description=(
        "A sealed vault beneath the Necropolis still contains an Undead sentinel following a command whose master is long gone. "
        "Stopping the old order is practical work, but also a warning about what freedom can fail to reach."
    ),
    objective_steps=(
        ("reach_vault", "Return EAST to the Necropolis Concourse and go DOWN into the Dead Command Vault."),
        ("fight_sentinel", "ATTACK SENTINEL and survive a real fight against the bound guardian."),
        ("break_sigil", "After the sentinel falls, BREAK SIGIL so the old command cannot simply seize it again."),
        ("complete", "You ended an order that had survived the person who gave it."),
    ),
)

UNDEAD_CHOSEN_REQUEST_QUEST = QuestDefinition(
    key=UNDEAD_CHOSEN_REQUEST_QUEST_KEY,
    name="A Request, Not an Order",
    style="structured",
    description=(
        "After the severance halls, memory archive, and command vault, your last lesson is intentionally ordinary. "
        "Someone in the Necropolis asks for help. You are allowed to say yes, and equally allowed to say no."
    ),
    objective_steps=(
        ("walk_market", "Go UP to the Concourse, EAST through Chisel Market, then SOUTH toward Freehands Court."),
        ("meet_freehand", "TALK TAL in Freehands Court."),
        ("choose_request", "Choose freely: HELP TAL or DECLINE TAL."),
        ("deliver_lamp", "If you chose to help, go SOUTH to the Desert Gate and DELIVER LAMP."),
        ("complete", "Your first civic decision was a choice rather than an embedded command."),
    ),
)

UNDEAD_START_QUESTS = (
    UNDEAD_NO_VOICE_QUEST,
    UNDEAD_MEMORY_QUEST,
    UNDEAD_REMAINING_ORDER_QUEST,
    UNDEAD_CHOSEN_REQUEST_QUEST,
)


BENT_BRASS_KEY = ItemDefinition(
    key=UNDEAD_MEMORY_KEY_ITEM,
    name="Bent Brass Key",
    description=(
        "A small ordinary brass key recovered with your remains. One tooth is bent and the bow is worn smooth. "
        "It does not identify a kingdom, family, profession, or owner. Whatever door it once opened is not written on it."
    ),
    category="keepsake",
    tier=0,
)

SHIELDED_LAMP_GLASS = ItemDefinition(
    key=UNDEAD_LAMP_GLASS_ITEM,
    name="Shielded Lamp Glass",
    description=(
        "A thick pane of smoked lamp glass wrapped in felt for the upper desert gate. It is civic repair material, not a relic, weapon, or badge of office."
    ),
    category="quest_item",
    tier=0,
)

BOUND_OSSUARY_SENTINEL = EnemyDefinition(
    key=UNDEAD_BOUND_SENTINEL_KEY,
    name="Bound Ossuary Sentinel",
    aliases=("sentinel", "bound sentinel", "ossuary sentinel", "guardian", "bound guardian"),
    description=(
        "a skeletal Undead guardian jerking through the same patrol it was commanded to perform generations ago, "
        "a dead master's sigil burning faintly across its sternum"
    ),
    max_hp=20,
    armor_class=2,
    auto_attack_damage=2,
    auto_attack_interval=3.2,
    xp_reward=25,
    retaliates=True,
    tutorial=False,
)


RECLAIMER_SEVRA = NpcDefinition(
    key=RECLAIMER_SEVRA_KEY,
    name="Reclaimer Sevra",
    short_description="a rune-marked skeleton in a gray work mantle checking recovery tags beside the stone slabs",
    room_key=UNDEAD_START_ROOM_KEY,
    role="newly freed Undead caretaker and first guide",
    dialogue=(
        "Sevra checks a slate, then checks you rather than the slate. 'Good. You are present.'",
        "'We recover bodies. We do not recover property. If anything still calls itself your master, we cut the call out.'",
    ),
)

KEEPER_ITH = NpcDefinition(
    key=KEEPER_ITH_KEY,
    name="Severance Keeper Ith",
    short_description="a narrow skeleton tending silver shears, chalk circles, and cracked command tablets",
    room_key=UNDEAD_SEVERANCE_HALL_KEY,
    role="specialist who removes surviving necromantic command bindings",
    dialogue=(
        "Ith rests both hands on the severance frame. 'We do not replace one master with a kinder one.'",
        "'The frame removes commands. What you do afterward is none of the frame's business.'",
    ),
)

ARCHIVIST_MERA = NpcDefinition(
    key=ARCHIVIST_MERA_KEY,
    name="Archivist Mera",
    short_description="a polished-bone archivist labeling modest recovery bundles instead of grand relics",
    room_key=UNDEAD_FORMER_LIVES_ARCHIVE_KEY,
    role="keeper of former-life effects and memory consent",
    dialogue=(
        "Mera gestures toward the shelves. 'A former life is evidence, not a sentence.'",
        "'Keep what helps. Give away what does not. Destroy what you refuse to carry. Nobody here gets a vote but you.'",
    ),
)

BONEWRIGHT_KELL = NpcDefinition(
    key=BONEWRIGHT_KELL_KEY,
    name="Bonewright Kell",
    short_description="a broad-framed skeleton fitting a replacement finger joint while arguing cheerfully over ceramic prices",
    room_key=UNDEAD_CHISEL_MARKET_KEY,
    role="bodywright and ordinary Necropolis craftsperson",
    dialogue=(
        "Kell holds a tiny hinge up to the light. 'Finger joint. Third one this decade. I keep telling people permanence is a sales pitch.'",
        "A potter across the aisle calls the price robbery. Kell answers, 'Then stop buying the good glaze.'",
    ),
)

FREEHAND_TAL = NpcDefinition(
    key=FREEHAND_TAL_KEY,
    name="Freehand Tal",
    short_description="a patched skeleton sorting voluntary work chits into piles marked urgent, useful, and whenever",
    room_key=UNDEAD_FREEHANDS_COURT_KEY,
    role="civic volunteer coordinator and final autonomy lesson",
    dialogue=(
        "Tal taps the three piles. 'Nobody here is assigned by command. Ask, bargain, volunteer, hire, refuse. The city still somehow gets repaired.'",
        "'Freedom includes disappointing somebody who asked nicely.'",
    ),
)

GATE_TENDER_ORRA = NpcDefinition(
    key=GATE_TENDER_ORRA_KEY,
    name="Gate Tender Orra",
    short_description="a weather-scoured skeleton tending shuttered lamps beside the stair into the desert glare",
    room_key=UNDEAD_DESERT_GATE_KEY,
    role="upper gate maintainer and world handoff contact",
    dialogue=(
        "Orra adjusts a smoked-glass shutter. 'Surface light does not hurt us. It is merely rude after a century underground.'",
        "'Road is yours when you want it. Coming back is yours too.'",
    ),
)

UNDEAD_START_NPCS = (
    RECLAIMER_SEVRA,
    KEEPER_ITH,
    ARCHIVIST_MERA,
    BONEWRIGHT_KELL,
    FREEHAND_TAL,
    GATE_TENDER_ORRA,
)


UNDEAD_START_ROOMS: tuple[RoomDefinition, ...] = (
    RoomDefinition(
        key=UNDEAD_START_ROOM_KEY,
        name="Reclamation Vault",
        region_key=UNDEAD_REGION_KEY,
        description=(
            "You lie on a clean basalt slab beneath a ceiling of black arches. Rows of other slabs stand empty or hold carefully tagged skeletal remains. "
            "No incense hides the mineral smell of the underground vault. No chanting necromancer stands above you. No voice occupies the inside of your skull. "
            "East, a silver-inlaid doorway leads to the Hall of Severed Orders. South, civic lamps mark the way toward the Necropolis proper."
        ),
        exits={"east": UNDEAD_SEVERANCE_HALL_KEY, "south": UNDEAD_CONCOURSE_KEY},
        npc_keys=(RECLAIMER_SEVRA_KEY,),
        tags=("undead_start", "reclamation", "quiet", "funerary", "safe"),
    ),
    RoomDefinition(
        key=UNDEAD_SEVERANCE_HALL_KEY,
        name="Hall of Severed Orders",
        region_key=UNDEAD_REGION_KEY,
        description=(
            "Silver lines divide the floor into work circles around a plain standing frame. Broken command tablets fill shallow wall niches, each cracked cleanly through its central sigil. "
            "The room looks ceremonial until you notice the practical shelves of chalk, wire, clamps, replacement joints, and record tags. This is surgery for old necromancy, not worship of it."
        ),
        exits={"west": UNDEAD_START_ROOM_KEY},
        npc_keys=(KEEPER_ITH_KEY,),
        tags=("undead_start", "severance", "necromancy", "autonomy", "safe"),
    ),
    RoomDefinition(
        key=UNDEAD_CONCOURSE_KEY,
        name="Necropolis Concourse",
        region_key=UNDEAD_REGION_KEY,
        description=(
            "A broad underground avenue opens beneath tiered stone galleries. Undead citizens cross between archive halls, workshops, courts, shrines, residences, and lift shafts descending deeper into the city. "
            "The architecture remains unmistakably funerary—sarcophagus-shaped doorways, memorial inscriptions, black stone—but the traffic is civic rather than mournful. "
            "West lies the Former Lives Archive. East, tool noise and bargaining carry from Chisel Market. A guarded stair descends to an old command vault."
        ),
        exits={
            "north": UNDEAD_START_ROOM_KEY,
            "west": UNDEAD_FORMER_LIVES_ARCHIVE_KEY,
            "east": UNDEAD_CHISEL_MARKET_KEY,
            "down": UNDEAD_COMMAND_VAULT_KEY,
        },
        tags=("undead_start", "necropolis", "civic_hub", "safe"),
    ),
    RoomDefinition(
        key=UNDEAD_FORMER_LIVES_ARCHIVE_KEY,
        name="Former Lives Archive",
        region_key=UNDEAD_REGION_KEY,
        description=(
            "Shelves of small boxes line a quiet chamber. Their labels are deliberately plain: location recovered, estimated age, objects found, marks on bone, known command sigils. "
            "Some bundles have names. Many do not. A central table holds the effects recovered with you: corroded cloth fasteners, a smooth river pebble, and a bent brass key."
        ),
        exits={"east": UNDEAD_CONCOURSE_KEY},
        npc_keys=(ARCHIVIST_MERA_KEY,),
        tags=("undead_start", "memory", "archive", "identity", "safe"),
    ),
    RoomDefinition(
        key=UNDEAD_CHISEL_MARKET_KEY,
        name="Chisel Market",
        region_key=UNDEAD_REGION_KEY,
        description=(
            "The market occupies a vaulted avenue bright with cold lamps and hand-painted shop signs. Bonewrights fit replacement joints beside clothiers who specialize in garments that hang correctly on skeletal frames. "
            "A potter argues with a metalworker over glaze prices. Two scribes heckle a street reciter for getting an old battle date wrong. Somebody farther down the arcade laughs loudly enough to echo through three arches. "
            "The Necropolis is eerie to outsiders. To the people shopping here, it is Tuesday."
        ),
        exits={"west": UNDEAD_CONCOURSE_KEY, "south": UNDEAD_FREEHANDS_COURT_KEY},
        npc_keys=(BONEWRIGHT_KELL_KEY,),
        tags=("undead_start", "market", "crafts", "ordinary_life", "safe"),
    ),
    RoomDefinition(
        key=UNDEAD_COMMAND_VAULT_KEY,
        name="Dead Command Vault",
        region_key=UNDEAD_REGION_KEY,
        description=(
            "A round chamber lies below newer Necropolis masonry. The older stones are carved with regiment numbers and obedience clauses whose author has been dead for generations. "
            "At the center, an ossuary sentinel repeats a four-point patrol without variation. A command sigil set into the floor flashes each time it turns."
        ),
        exits={"up": UNDEAD_CONCOURSE_KEY},
        tags=("undead_start", "old_necromancy", "combat", "command_binding"),
    ),
    RoomDefinition(
        key=UNDEAD_FREEHANDS_COURT_KEY,
        name="Freehands Court",
        region_key=UNDEAD_REGION_KEY,
        description=(
            "A civic court has been built around a wall covered in removable work chits. Repairs, deliveries, archive copying, escort work, paid contracts, and volunteer requests all hang side by side. "
            "People take chits down, put them back, argue over compensation, or write NO beneath unreasonable offers. Nobody is assigned a task merely because they are standing here. "
            "North returns to the market. South, an ascending passage leads toward the desert gate."
        ),
        exits={"north": UNDEAD_CHISEL_MARKET_KEY, "south": UNDEAD_DESERT_GATE_KEY},
        npc_keys=(FREEHAND_TAL_KEY,),
        tags=("undead_start", "civic", "choice", "voluntary_labor", "safe"),
    ),
    RoomDefinition(
        key=UNDEAD_DESERT_GATE_KEY,
        name="Upper Desert Gate",
        region_key=UNDEAD_REGION_KEY,
        description=(
            "The underground road ends at a high stone gate where baffled shafts admit hard desert light without flooding the Necropolis below. Smoked-glass lamps line the last ascent. "
            "Beyond the eastern gate, pale sand and black ruins shimmer beneath an enormous sky. The free city continues behind you; the wider world begins ahead."
        ),
        exits={"north": UNDEAD_FREEHANDS_COURT_KEY, "east": UNDEAD_SUNSCAR_ROAD_KEY},
        npc_keys=(GATE_TENDER_ORRA_KEY,),
        tags=("undead_start", "city_gate", "desert", "world_handoff", "safe"),
    ),
    RoomDefinition(
        key=UNDEAD_SUNSCAR_ROAD_KEY,
        name="Sunscar Road",
        region_key=UNDEAD_REGION_KEY,
        description=(
            "A stone road crosses the desolate desert between half-buried ruins and wind-cut markers. Behind you, the Necropolis entrance disappears into a black escarpment until only its gate lamps betray it. "
            "Heat trembles above the sand. You do not breathe it, hunger in it, or thirst beneath it. For the first time since waking, there is no ritual, old command, or civic lesson waiting at the next marker. "
            "The road simply continues into Astralis."
        ),
        exits={"west": UNDEAD_DESERT_GATE_KEY},
        tags=("outside_necropolis", "desert", "world_handoff", "undead_identity"),
    ),
)


def _feature(key: str, name: str, summary: str, examine: str, aliases: tuple[str, ...] = (), *, listen: str = "", search: str = "", touch: str = "") -> FeatureDefinition:
    return FeatureDefinition(
        key=key,
        name=name,
        aliases=aliases,
        summary=summary,
        examine_text=examine,
        listen_text=listen,
        search_text=search,
        touch_text=touch,
    )


def _exit(direction: str, destination: str, name: str, travel: str) -> ExitDefinition:
    return ExitDefinition(direction=direction, destination_key=destination, name=name, travel_text=travel)


def _layer(key: str, text: str, priority: int = 45) -> DescriptionLayer:
    return DescriptionLayer(key=key, text=text, priority=priority, condition=ViewCondition())


def undead_room_augmentations() -> dict[str, RoomAugmentation]:
    return {
        UNDEAD_START_ROOM_KEY: RoomAugmentation(
            exit_overrides=(
                _exit("east", UNDEAD_SEVERANCE_HALL_KEY, "Hall of Severed Orders", "You step beneath the silver-inlaid arch into the severance hall."),
                _exit("south", UNDEAD_CONCOURSE_KEY, "Necropolis Concourse", "You follow the civic lamps south into the free Necropolis."),
            ),
            features=(
                _feature(
                    "reclamation_slabs", "Reclamation Slabs", "clean basalt slabs for newly recovered dead",
                    "Each slab has drainage grooves, joint braces, a blank name plate, and a tag hook. The blank plate is intentional: the Reclaimers do not assign a recovered body the identity of whoever once owned its bones.",
                    ("slabs", "slab", "stone slab", "reclamation slab"),
                ),
                _feature(
                    "silent_command_arch", "Silent Command Arch", "a black arch once used to detect active necromantic orders",
                    "Hair-thin silver wire runs through the arch. When active command magic passes beneath it, the wire is meant to sing. It is silent now.",
                    ("arch", "command arch", "silver arch"),
                    listen="Nothing hums in the silver wire. More importantly, nothing speaks inside you either.",
                ),
            ),
            description_layers=(_layer("reclamation_stillness", "The unsettling thing is not death. It is the absence of instruction."),),
        ),
        UNDEAD_SEVERANCE_HALL_KEY: RoomAugmentation(
            exit_overrides=(_exit("west", UNDEAD_START_ROOM_KEY, "Reclamation Vault", "You leave the silver circles and return to the recovery slabs."),),
            features=(
                _feature(
                    "severance_frame", "Severance Frame", "a plain standing frame threaded with silver wire",
                    "The frame is built to catch old command magic when an Undead steps inside it. Cracked tablets around the base record bindings already cut away.",
                    ("frame", "severance frame", "silver frame"),
                ),
                _feature(
                    "command_scar", "Command Scar", "a faint necromantic line crossing the inside of your sternum",
                    "The mark is not a name or heraldry. It is syntax: an old magical route by which another will could once reach yours. Most of it is dead, but one thread remains attached.",
                    ("binding", "command scar", "scar", "order mark", "command mark"),
                ),
                _feature(
                    "broken_order_tablets", "Broken Order Tablets", "rows of command tablets cracked through their central sigils",
                    "Some orders are military. Some are domestic. Some are only a single word repeated forever. The hall displays them as evidence of abolished ownership, not trophies.",
                    ("tablets", "orders", "broken tablets"),
                ),
            ),
            description_layers=(_layer("severance_rule", "Nothing in the hall asks what useful work your former master intended you to perform. Usefulness does not preserve a claim of ownership."),),
        ),
        UNDEAD_CONCOURSE_KEY: RoomAugmentation(
            exit_overrides=(
                _exit("north", UNDEAD_START_ROOM_KEY, "Reclamation Vault", "You climb toward the quieter recovery vaults."),
                _exit("west", UNDEAD_FORMER_LIVES_ARCHIVE_KEY, "Former Lives Archive", "You enter the archive of recovered personal effects."),
                _exit("east", UNDEAD_CHISEL_MARKET_KEY, "Chisel Market", "You follow the sound of tools and bargaining into the market."),
                _exit("down", UNDEAD_COMMAND_VAULT_KEY, "Dead Command Vault", "You descend the guarded stair into older necromantic masonry."),
            ),
            features=(
                _feature(
                    "civic_direction_stela", "Civic Direction Stela", "a stone directory listing courts, shrines, workshops, archives, and lifts",
                    "The directory is mundane enough to undermine the atmosphere: bodywright permits on level four, memorial records on level two, lift inspections delayed until sixth bell.",
                    ("directory", "stela", "sign", "directions"),
                ),
                _feature(
                    "public_memorial_band", "Public Memorial Band", "a continuous line of names carved around the concourse wall",
                    "The names include former-life names, chosen names, titles, nicknames, and many entries marked UNKNOWN AT RECLAMATION. The city records what people chose to answer to after freedom.",
                    ("memorial", "names", "name band"),
                ),
            ),
            description_layers=(_layer("concourse_life", "A messenger hurries past with tax tablets. Two neighbors argue over a borrowed chisel. Death did not make civic life less petty, complicated, or alive with preference."),),
        ),
        UNDEAD_FORMER_LIVES_ARCHIVE_KEY: RoomAugmentation(
            exit_overrides=(_exit("east", UNDEAD_CONCOURSE_KEY, "Necropolis Concourse", "You leave the recovery shelves for the broader concourse."),),
            features=(
                _feature(
                    "recovery_effects", "Recovered Effects", "the few ordinary objects found with your remains",
                    "A corroded fastening, a river-smoothed pebble, and a bent brass key sit on plain cloth. None proves who you were. The archive refuses to build a grand biography from three objects.",
                    ("effects", "recovered effects", "objects", "belongings"),
                ),
                _feature(
                    "bent_key_display", "Bent Brass Key", "a small worn key with one damaged tooth",
                    "The bow is polished from years of handling. It might once have opened a home, workshop, chest, gate, or nothing important at all.",
                    ("key", "brass key", "bent key"),
                    touch="The brass is cold. For an instant you remember pushing a swollen wooden door with one shoulder while rain ran down somebody's roof. Someone inside complained about the mud. The memory ends before you see a face.",
                ),
                _feature(
                    "unclaimed_shelves", "Unclaimed Shelves", "rows of recovery bundles that no current Undead chose to keep",
                    "Some are donated for study. Some wait in case memory returns decades later. Empty spaces mark bundles deliberately destroyed at the recovered person's request.",
                    ("shelves", "bundles", "unclaimed effects"),
                ),
            ),
            description_layers=(_layer("archive_consent", "The archive preserves evidence carefully and attachment reluctantly. Memory belongs to the person remembering, not to the institution storing the box."),),
        ),
        UNDEAD_CHISEL_MARKET_KEY: RoomAugmentation(
            exit_overrides=(
                _exit("west", UNDEAD_CONCOURSE_KEY, "Necropolis Concourse", "You leave the crowded arcade for the main concourse."),
                _exit("south", UNDEAD_FREEHANDS_COURT_KEY, "Freehands Court", "You pass beneath a painted WORK OFFERED / WORK WANTED arch into Freehands Court."),
            ),
            features=(
                _feature(
                    "bonewright_stall", "Bonewright Stall", "a workbench covered in joint pins, resin, wire, and polished replacement bone",
                    "Repairs range from structural splints to decorative finger caps. The price board has separate columns for materials, labor, and 'customer changed their mind halfway through.'",
                    ("stall", "bonewright", "workbench", "joint stall"),
                ),
                _feature(
                    "market_argument", "Ceramic Argument", "a potter and metalworker conducting a loud disagreement over glaze prices",
                    "Neither participant appears angry enough to leave. Three nearby merchants are openly taking sides. One has started accepting tiny bets.",
                    ("argument", "potter", "metalworker", "glaze"),
                    listen="'That glaze costs more every season!' 'Then stop breaking bowls every season!' Laughter travels down the arcade.",
                ),
                _feature(
                    "street_reciter", "Street Reciter", "a skeletal performer reciting an old battle chronicle to a highly critical audience",
                    "Two scribes interrupt every inaccurate date. The reciter has started changing dates on purpose just to make them shout.",
                    ("reciter", "poet", "performer", "scribes"),
                ),
            ),
            description_layers=(_layer("market_normalcy", "The ordinary noise matters after the reclamation vault: nobody here is waiting for a master to tell them what to buy, make, argue about, or find funny."),),
        ),
        UNDEAD_COMMAND_VAULT_KEY: RoomAugmentation(
            exit_overrides=(_exit("up", UNDEAD_CONCOURSE_KEY, "Necropolis Concourse", "You climb out of the old command chamber into newer civic stone."),),
            features=(
                _feature(
                    "floor_command_sigil", "Floor Command Sigil", "an old obedience sigil pulsing beneath the sentinel's patrol",
                    "The sigil is a command relay. Its master is dead, but the instruction remains: guard this chamber, recognize no new authority, repeat until destroyed.",
                    ("sigil", "command sigil", "floor sigil", "order sigil"),
                ),
                _feature(
                    "obedience_clauses", "Obedience Clauses", "lines of necromantic instruction carved into the old wall",
                    "The writing does not threaten punishment or promise reward. It simply assumes that the body reading it cannot refuse. That assumption is what the newer Necropolis was built to reject.",
                    ("clauses", "wall writing", "orders", "carvings"),
                ),
            ),
            description_layers=(_layer("vault_warning", "Every turn of the sentinel's patrol lands at exactly the same angle. Nothing in the movement is chosen."),),
        ),
        UNDEAD_FREEHANDS_COURT_KEY: RoomAugmentation(
            exit_overrides=(
                _exit("north", UNDEAD_CHISEL_MARKET_KEY, "Chisel Market", "You return to the market arcade."),
                _exit("south", UNDEAD_DESERT_GATE_KEY, "Upper Desert Gate", "You follow the rising passage toward the upper gate and desert light."),
            ),
            features=(
                _feature(
                    "work_chit_wall", "Work Chit Wall", "a wall of removable requests, contracts, and volunteer jobs",
                    "Some requests offer coin. Some offer barter. Some simply ask. Several have NO written across them with counteroffers underneath. The wall treats refusal as part of negotiation, not disobedience.",
                    ("wall", "chits", "work chits", "job board", "request wall"),
                ),
                _feature(
                    "refusal_bowl", "Refusal Bowl", "a stone bowl filled with discarded or declined work chits",
                    "A little plaque reads: A REQUEST SURVIVES NO BETTER BY PRETENDING TO BE AN ORDER. The bowl is emptied for recycling every few days.",
                    ("bowl", "refusal bowl", "declined chits"),
                ),
            ),
            description_layers=(_layer("freehands_custom", "People ask each other for things constantly here. The cultural line is not between asking and silence; it is between asking and claiming the answer in advance."),),
        ),
        UNDEAD_DESERT_GATE_KEY: RoomAugmentation(
            exit_overrides=(
                _exit("north", UNDEAD_FREEHANDS_COURT_KEY, "Freehands Court", "You descend toward the civic courts and market."),
                _exit("east", UNDEAD_SUNSCAR_ROAD_KEY, "Sunscar Road", "You pass through the upper gate into the white desert glare."),
            ),
            features=(
                _feature(
                    "smoked_gate_lamps", "Smoked Gate Lamps", "heavy lamps shielded behind dark glass against sand and glare",
                    "The lamps guide travelers back to the almost-hidden gate at night and through dust storms. One frame is waiting for replacement glass.",
                    ("lamps", "gate lamps", "lamp", "smoked lamps"),
                ),
                _feature(
                    "desert_shutters", "Desert Shutters", "layered stone and bronze shutters controlling sand entering the Necropolis",
                    "The shutters are maintenance-intensive and entirely ordinary. The free Undead built a city in a hostile desert; autonomy did not abolish chores.",
                    ("shutters", "gate shutters", "bronze shutters"),
                ),
            ),
            description_layers=(_layer("gate_choice", "The gate is designed to keep weather out, not citizens in."),),
        ),
        UNDEAD_SUNSCAR_ROAD_KEY: RoomAugmentation(
            exit_overrides=(_exit("west", UNDEAD_DESERT_GATE_KEY, "Upper Desert Gate", "You follow the black stone markers back toward the hidden Necropolis entrance."),),
            features=(
                _feature(
                    "black_road_markers", "Black Road Markers", "waist-high stones marking a safe line across shifting sand",
                    "Each marker gives distance back to the Necropolis and points toward roads not yet authored into the local starter region. None orders you to follow them.",
                    ("markers", "road markers", "stones", "posts"),
                ),
                _feature(
                    "half_buried_ruins", "Half-Buried Ruins", "old walls protruding from pale sand beyond the road",
                    "Some ruins predate the free Necropolis. Others belonged to necromancers whose servants eventually outlived their commands. The desert does not label which is which from a distance.",
                    ("ruins", "old ruins", "buried ruins"),
                ),
            ),
            description_layers=(_layer("outside_freedom", "There is no missing voice to replace out here. Silence is no longer evidence that an order failed to arrive. It is simply silence."),),
        ),
    }


def _replace_room(room: RoomDefinition) -> None:
    if room.key in legacy_world.ROOMS_BY_KEY:
        legacy_world.ROOMS = tuple(room if old.key == room.key else old for old in legacy_world.ROOMS)
    else:
        legacy_world.ROOMS = legacy_world.ROOMS + (room,)
    legacy_world.ROOMS_BY_KEY[room.key] = room


def _replace_npc(npc: NpcDefinition) -> None:
    if npc.key in legacy_world.NPCS_BY_KEY:
        legacy_world.NPCS = tuple(npc if old.key == npc.key else old for old in legacy_world.NPCS)
    else:
        legacy_world.NPCS = legacy_world.NPCS + (npc,)
    legacy_world.NPCS_BY_KEY[npc.key] = npc


def _patch_undead_identity() -> None:
    current = character_options.RACES_BY_KEY.get("undead")
    if current is None:
        return
    updated = replace(
        current,
        name="Undead",
        description=(
            "Literal skeletal Undead descended from necromantically reanimated servants, soldiers, and laborers who survived the masters and command systems that once owned them. "
            "Free Undead built a civilization around severance, memory, consent, chosen bonds, and the difficult question of what a person becomes after an imposed purpose ends."
        ),
        lore=(
            "Undead are literally reanimated skeletal dead, not merely gaunt living people or a death-touched biological species.",
            "Many were originally raised by necromancers as soldiers, laborers, guards, servants, or other commanded tools.",
            "When masters died, command networks failed, or bindings were deliberately severed, some Undead retained or developed independent personhood and escaped the purposes imposed on them.",
            "Free Undead gathered into a vast underground Necropolis beneath the desolate desert; newly recovered bound dead are brought through reclamation and severance before joining civic life.",
            "Memory varies from detailed former-life recollection to isolated fragments. The free Necropolis treats a former identity as belonging to the individual, who may preserve, reinterpret, ignore, donate, or destroy its remnants.",
            "Undead do not need food, drink, sleep, or breath, though their bodies require repair and can eventually deteriorate beyond recovery.",
            "Necromancy is culturally complicated rather than automatically forbidden. Reanimation and death magic are familiar; claiming ownership of a self-aware Undead through binding magic is among the culture's clearest moral taboos.",
            "Simple animated remains and fully self-aware Undead are not automatically treated as the same thing. Personhood, will, and the capacity to refuse matter more than the material of a body.",
            "Other peoples often call them Skeletons as a literal description and generally remain uneasy around them. Their central identity is not built around reclaiming an outsider insult, but around freedom after ownership.",
            "Ordinary healing magic works normally on Undead, while poison and disease affect them less strongly than living peoples.",
            "The Necropolis looks funerary and eerie, but it contains ordinary markets, crafts, arguments, jokes, contracts, friendships, and voluntary obligations like any other city.",
        ),
        social_profile="feared_literal_undead_with_free_society",
    )
    character_options.RACES = tuple(updated if race.key == "undead" else race for race in character_options.RACES)
    character_options.RACES_BY_KEY["undead"] = updated


def install_undead_content(world_service=None) -> None:
    """Register the free-Undead identity, starter region, quests, and tutorial combat."""
    _patch_undead_identity()

    for quest in UNDEAD_START_QUESTS:
        if quest.key not in quests.QUESTS_BY_KEY:
            quests.QUESTS = quests.QUESTS + (quest,)
        quests.QUESTS_BY_KEY[quest.key] = quest

    for item in (BENT_BRASS_KEY, SHIELDED_LAMP_GLASS):
        if item.key not in crafting.ITEMS_BY_KEY:
            crafting.ITEMS = crafting.ITEMS + (item,)
        crafting.ITEMS_BY_KEY[item.key] = item

    if UNDEAD_BOUND_SENTINEL_KEY not in combat.ENEMIES_BY_KEY:
        combat.ENEMIES = combat.ENEMIES + (BOUND_OSSUARY_SENTINEL,)
    combat.ENEMIES_BY_KEY[UNDEAD_BOUND_SENTINEL_KEY] = BOUND_OSSUARY_SENTINEL

    for npc in UNDEAD_START_NPCS:
        _replace_npc(npc)
    for room in UNDEAD_START_ROOMS:
        _replace_room(room)

    if world_service is not None:
        for room in UNDEAD_START_ROOMS:
            world_service.legacy_rooms[room.key] = room
        world_service.augmentations.update(undead_room_augmentations())
        cache = getattr(world_service, "_scene_cache", None)
        if cache is not None:
            for room_key in UNDEAD_START_ROOM_KEYS:
                cache.pop(room_key, None)


def _flags(session) -> set[str]:
    if session.character is None:
        return set()
    return set(session.database.list_flags(session.character.id))


def _quest(session, key: str):
    if session.character is None:
        return None
    return session.database.get_quest(session.character.id, key)


def _active_step(session, key: str) -> str | None:
    row = _quest(session, key)
    if row and row.get("status") == "active":
        return row.get("current_step")
    return None


def _current_opening_quest(session):
    for definition in UNDEAD_START_QUESTS:
        row = _quest(session, definition.key)
        if row and row.get("status") == "active":
            return definition, row
    return None, None


def _refresh_character(session) -> None:
    if session.character is None:
        return
    refreshed = session.database.get_character_by_name(session.character.name)
    if refreshed is not None:
        session.character = refreshed


def prepare_undead_start(session) -> bool:
    """Place new/legacy Undead into the authored start without touching level or inventory progress."""
    if session.character is None or session.character.race != "undead":
        return False
    changed = False
    if not session.character.current_room:
        session.database.set_character_room(session.character.id, UNDEAD_START_ROOM_KEY)
        changed = True
    if not session.character.bind_room:
        session.database.set_bind_room(session.character.id, UNDEAD_START_ROOM_KEY)
        changed = True
    if _quest(session, UNDEAD_NO_VOICE_QUEST.key) is None and UNDEAD_OPENING_COMPLETE_FLAG not in _flags(session):
        session.database.start_quest(session.character.id, UNDEAD_NO_VOICE_QUEST.key, "listen_silence")
        changed = True
    if changed:
        _refresh_character(session)
    return changed


def _complete_quest(session, definition: QuestDefinition, complete_flag: str | None = None) -> None:
    assert session.character is not None
    session.database.complete_quest(session.character.id, definition.key)
    if complete_flag:
        session.database.grant_flag(session.character.id, complete_flag)


def _start_next(session, definition: QuestDefinition, step: str) -> None:
    assert session.character is not None
    if _quest(session, definition.key) is None:
        session.database.start_quest(session.character.id, definition.key, step)


async def _show_undead_status(session) -> None:
    definition, row = _current_opening_quest(session)
    await session.send("\r\n--- Reclamation Record ---\r\n")
    if definition is None or row is None:
        if UNDEAD_OPENING_COMPLETE_FLAG in _flags(session):
            await session.send("Opening status: unbound and free to leave the Necropolis.\r\n")
        else:
            await session.send("No active reclamation duty.\r\n")
        return
    await session.send(f"Current thread: {definition.name}.\r\n")
    objective = definition.objective_for_step(row.get("current_step"))
    if objective:
        await session.send(f"Objective: {objective}\r\n")


async def handle_undead_start_command(session, command: str) -> bool:
    if session.character is None or session.character.race != "undead":
        return False
    normalized = command.strip().lower()
    room = session.character.current_room

    if normalized in {"reclamation", "unbound", "severance", "freedom", "undead start", "opening"}:
        await _show_undead_status(session)
        return True

    no_voice_step = _active_step(session, UNDEAD_NO_VOICE_QUEST.key)
    memory_step = _active_step(session, UNDEAD_MEMORY_QUEST.key)
    order_step = _active_step(session, UNDEAD_REMAINING_ORDER_QUEST.key)
    request_step = _active_step(session, UNDEAD_CHOSEN_REQUEST_QUEST.key)

    if room == UNDEAD_START_ROOM_KEY and normalized in {"listen", "listen for master", "listen for voice", "listen command", "listen for command"}:
        if no_voice_step == "listen_silence":
            session.database.grant_flag(session.character.id, UNDEAD_MASTER_SILENCE_HEARD_FLAG)
            session.database.advance_quest(session.character.id, UNDEAD_NO_VOICE_QUEST.key, "talk_reclaimer")
            await session.send(
                "\r\nYou wait for the pressure behind thought: march, guard, kneel, carry, kill—whatever word once arrived already shaped like obedience.\r\n"
                "Nothing comes.\r\n"
                "You hear the click of Reclaimer Sevra's finger bones against a slate, distant wheels in the corridor, and your own joints settling on the basalt. The silence inside you remains yours.\r\n"
                "TALK RECLAIMER.\r\n"
            )
            return True
        await session.send("\r\nThere is still no master's voice inside you. The absence no longer feels accidental.\r\n")
        return True

    if room == UNDEAD_START_ROOM_KEY and normalized in {
        "talk reclaimer", "talk to reclaimer", "talk sevra", "talk to sevra", "talk reclaimer sevra", "talk to reclaimer sevra"
    }:
        if no_voice_step == "talk_reclaimer":
            session.database.grant_flag(session.character.id, UNDEAD_RECLAIMER_HEARD_FLAG)
            session.database.advance_quest(session.character.id, UNDEAD_NO_VOICE_QUEST.key, "inspect_binding")
            await session.send(
                "\r\nSevra does not ask your former name. 'We found you in an old service crypt under a collapsed command post. The necromancer who owned that place is dust.'\r\n"
                "'That does not mean every order died with them. Old bindings can keep moving a body long after there is nobody left to benefit.'\r\n"
                "Sevra points east. 'The Hall of Severed Orders checks what remains. Understand this before you go: we are not transferring ownership from the dead master to the Necropolis. Nobody here owns you either.'\r\n"
                "Go EAST and EXAMINE BINDING.\r\n"
            )
            return True
        await session.send("\r\nSevra checks another recovery tag. 'Presence first. History later, if you want it.'\r\n")
        return True

    if room == UNDEAD_SEVERANCE_HALL_KEY and normalized in {
        "examine binding", "look binding", "examine command scar", "look command scar", "inspect binding", "examine scar"
    }:
        if no_voice_step == "inspect_binding":
            session.database.grant_flag(session.character.id, UNDEAD_BINDING_EXAMINED_FLAG)
            session.database.advance_quest(session.character.id, UNDEAD_NO_VOICE_QUEST.key, "sever_orders")
            await session.send(
                "\r\nIn the severance frame, a silver thread of old magic becomes visible across the inside of your sternum. Most of the command route is inert. One final line still waits for authority that will never return.\r\n"
                "Keeper Ith says, 'A dead master can still own centuries if nobody bothers to cut the grammar.'\r\n"
                "SEVER ORDERS.\r\n"
            )
            return True
        await session.send("\r\nThe command scar is only a dead line now. Whatever once traveled through it no longer reaches you.\r\n")
        return True

    if room == UNDEAD_SEVERANCE_HALL_KEY and normalized in {
        "sever orders", "sever order", "break orders", "cut orders", "sever binding", "cut binding", "use severance frame"
    }:
        if no_voice_step != "sever_orders":
            await session.send("\r\nThe frame has no active binding ready to cut at this stage.\r\n")
            return True
        session.database.grant_flag(session.character.id, UNDEAD_ORDERS_SEVERED_FLAG)
        _complete_quest(session, UNDEAD_NO_VOICE_QUEST)
        _start_next(session, UNDEAD_MEMORY_QUEST, "reach_archive")
        await session.send(
            "\r\nIth closes the silver contacts around the command scar. There is no flash. The remaining thread simply parts.\r\n"
            "For one impossible instant you expect the emptiness to be replaced by another voice. It is not.\r\n"
            "Ith opens the frame. 'Finished. There is no oath to us. No required gratitude. Walk out when you choose.'\r\n"
            "\r\nQuest complete: No Voice Above You.\r\n"
            "New quest: What Was Yours. Go WEST, then SOUTH to the Necropolis Concourse and WEST into the Former Lives Archive.\r\n"
        )
        return True

    if room == UNDEAD_FORMER_LIVES_ARCHIVE_KEY and normalized in {
        "examine effects", "look effects", "inspect effects", "examine belongings", "look belongings", "examine recovered effects"
    }:
        if memory_step == "examine_effects":
            session.database.grant_flag(session.character.id, UNDEAD_EFFECTS_EXAMINED_FLAG)
            session.database.advance_quest(session.character.id, UNDEAD_MEMORY_QUEST.key, "touch_key")
            await session.send(
                "\r\nArchivist Mera lays out three things recovered near your bones: a corroded fastening, a river-smoothed pebble, and a bent brass key.\r\n"
                "'None of these proves a life,' Mera says. 'We do not build you a personality from pocket debris.'\r\n"
                "The key's bow is worn smooth by repeated handling. TOUCH KEY.\r\n"
            )
            return True
        await session.send("\r\nThe recovered effects remain ordinary objects. The archive will not tell you what they are supposed to mean.\r\n")
        return True

    if room == UNDEAD_FORMER_LIVES_ARCHIVE_KEY and normalized in {
        "touch key", "touch brass key", "touch bent key", "hold key", "pick up key"
    }:
        if memory_step == "touch_key":
            if session.database.item_quantity(session.character.id, UNDEAD_MEMORY_KEY_ITEM) <= 0:
                session.database.add_item(session.character.id, UNDEAD_MEMORY_KEY_ITEM, 1)
            session.database.grant_flag(session.character.id, UNDEAD_MEMORY_SPARKED_FLAG)
            session.database.advance_quest(session.character.id, UNDEAD_MEMORY_QUEST.key, "choose_memory")
            await session.send(
                "\r\nThe brass touches your fingers.\r\n"
                "Rain. A swollen wooden door. You lean one shoulder into it because the key turns but the frame sticks. Someone on the other side complains about the mud you are bringing in. You remember being annoyed. You almost remember laughing.\r\n"
                "Then the fragment ends. No face. No name. No revelation about who you were meant to be.\r\n"
                "Mera waits. 'It is yours now because you are holding it, not because a dead version of you demands anything.'\r\n"
                "Choose: KEEP KEY, DONATE KEY, or DESTROY KEY. None is the correct answer.\r\n"
            )
            return True
        await session.send("\r\nThe key is cold brass and an ordinary fragment of a life. It offers no additional memory on command.\r\n")
        return True

    if room == UNDEAD_FORMER_LIVES_ARCHIVE_KEY and normalized in {
        "keep key", "keep the key", "donate key", "donate the key", "destroy key", "destroy the key"
    }:
        if memory_step != "choose_memory":
            await session.send("\r\nThere is no former-life choice waiting for you at this point.\r\n")
            return True
        if normalized.startswith("keep"):
            session.database.grant_flag(session.character.id, UNDEAD_MEMORY_KEEP_FLAG)
            text = (
                "You close your hand around the bent key and keep it. Mera records only: RETAINED BY OWNER.\r\n"
                "The memory does not become an obligation simply because you chose to carry its object."
            )
        elif normalized.startswith("donate"):
            session.database.grant_flag(session.character.id, UNDEAD_MEMORY_DONATE_FLAG)
            session.database.consume_item(session.character.id, UNDEAD_MEMORY_KEY_ITEM, 1)
            text = (
                "You return the key to Mera for the archive. The label changes from RECOVERED WITH REMAINS to DONATED BY OWNER.\r\n"
                "The distinction is small enough to fit on one line and important enough that Mera writes it carefully."
            )
        else:
            session.database.grant_flag(session.character.id, UNDEAD_MEMORY_DESTROY_FLAG)
            session.database.consume_item(session.character.id, UNDEAD_MEMORY_KEY_ITEM, 1)
            text = (
                "At your request, Mera places the key in a small cutting press. The brass folds, snaps, and drops into a scrap bin for melting.\r\n"
                "Nobody asks you to explain why a former life was not entitled to preservation."
            )
        _complete_quest(session, UNDEAD_MEMORY_QUEST)
        _start_next(session, UNDEAD_REMAINING_ORDER_QUEST, "reach_vault")
        await session.send(
            "\r\n" + text + "\r\n\r\nQuest complete: What Was Yours.\r\n"
            "New quest: The Order That Remains. Return EAST to the Concourse and go DOWN into the Dead Command Vault.\r\n"
        )
        return True

    if room == UNDEAD_COMMAND_VAULT_KEY and normalized in {
        "break sigil", "break command sigil", "destroy sigil", "sever sigil", "smash sigil", "break order sigil"
    }:
        if order_step == "fight_sentinel":
            await session.send("\r\nThe sentinel is still carrying out the order. You cannot safely reach the sigil while it patrols. ATTACK SENTINEL.\r\n")
            return True
        if order_step != "break_sigil":
            await session.send("\r\nThe old floor sigil has no active role in your current task.\r\n")
            return True
        session.database.grant_flag(session.character.id, UNDEAD_COMMAND_SIGIL_BROKEN_FLAG)
        _complete_quest(session, UNDEAD_REMAINING_ORDER_QUEST)
        _start_next(session, UNDEAD_CHOSEN_REQUEST_QUEST, "walk_market")
        await session.send(
            "\r\nYou drive the loose iron wedge beneath the command stone and lever upward. The sigil cracks through its central line. The faint pressure in the room vanishes.\r\n"
            "The fallen sentinel does not rise again. Reclaimers will examine it later for any self that may remain beneath the old order. The point was never to destroy obedience by destroying every body that suffered it.\r\n"
            "\r\nQuest complete: The Order That Remains.\r\n"
            "New quest: A Request, Not an Order. Go UP to the Concourse, EAST through Chisel Market, then SOUTH to Freehands Court.\r\n"
        )
        return True

    if room == UNDEAD_FREEHANDS_COURT_KEY and normalized in {
        "talk tal", "talk to tal", "talk freehand", "talk to freehand", "talk freehand tal", "talk to freehand tal"
    }:
        if request_step == "meet_freehand":
            session.database.grant_flag(session.character.id, UNDEAD_REQUEST_HEARD_FLAG)
            session.database.advance_quest(session.character.id, UNDEAD_CHOSEN_REQUEST_QUEST.key, "choose_request")
            await session.send(
                "\r\nTal holds up a felt-wrapped pane of smoked lamp glass. 'Upper gate lost one to a sand gust. I could use somebody carrying this south.'\r\n"
                "Tal then puts the pane back on the table instead of into your hands. 'That was a request. Important distinction around here.'\r\n"
                "'If you want it, HELP TAL. If you do not, DECLINE TAL. Gate still opens either way.'\r\n"
            )
            return True
        await session.send("\r\nTal sorts another work chit. 'Ask. Pay when promised. Accept no. Civilization.'\r\n")
        return True

    if room == UNDEAD_FREEHANDS_COURT_KEY and normalized in {
        "help tal", "help freehand", "accept request", "accept tal", "i will help", "yes help"
    }:
        if request_step != "choose_request":
            await session.send("\r\nTal has no unresolved request for you right now.\r\n")
            return True
        if session.database.item_quantity(session.character.id, UNDEAD_LAMP_GLASS_ITEM) <= 0:
            session.database.add_item(session.character.id, UNDEAD_LAMP_GLASS_ITEM, 1)
        session.database.grant_flag(session.character.id, UNDEAD_REQUEST_HELP_FLAG)
        session.database.advance_quest(session.character.id, UNDEAD_CHOSEN_REQUEST_QUEST.key, "deliver_lamp")
        await session.send(
            "\r\n'I will help,' you say—or the equivalent your jaw and voice make now.\r\n"
            "Tal hands you the wrapped glass. Nothing closes around the decision afterward. No magical hook, no compulsion, no punishment clause. You can feel the weight because you chose to pick it up.\r\n"
            "Go SOUTH to the Upper Desert Gate and DELIVER LAMP.\r\n"
        )
        return True

    if room == UNDEAD_FREEHANDS_COURT_KEY and normalized in {
        "decline tal", "decline freehand", "decline request", "refuse request", "no", "no thanks"
    }:
        if request_step != "choose_request":
            await session.send("\r\nThere is no unresolved request to decline now.\r\n")
            return True
        session.database.grant_flag(session.character.id, UNDEAD_REQUEST_DECLINE_FLAG)
        _complete_quest(session, UNDEAD_CHOSEN_REQUEST_QUEST)
        session.database.grant_flag(session.character.id, UNDEAD_OPENING_COMPLETE_FLAG)
        await session.send(
            "\r\n'No,' you say.\r\n"
            "Tal nods and moves the lamp-glass chit back into the useful pile. 'All right.'\r\n"
            "That is the entire consequence. No anger. No hidden command waiting beneath the polite wording. Somebody else will take it, or the gate tender will fetch it later.\r\n"
            "Tal points south. 'Road is still yours.'\r\n"
            "\r\nQuest complete: A Request, Not an Order.\r\n"
            "Your reclamation opening is complete. The Upper Desert Gate lies SOUTH.\r\n"
        )
        return True

    if room == UNDEAD_DESERT_GATE_KEY and normalized in {
        "deliver lamp", "deliver glass", "deliver lamp glass", "give lamp", "give glass", "give lamp glass"
    }:
        if request_step != "deliver_lamp":
            await session.send("\r\nGate Tender Orra is not expecting a delivery from you right now.\r\n")
            return True
        if session.database.item_quantity(session.character.id, UNDEAD_LAMP_GLASS_ITEM) <= 0:
            await session.send("\r\nYou are not carrying the shielded lamp glass Tal gave you.\r\n")
            return True
        session.database.consume_item(session.character.id, UNDEAD_LAMP_GLASS_ITEM, 1)
        session.database.grant_flag(session.character.id, UNDEAD_LAMP_DELIVERED_FLAG)
        _complete_quest(session, UNDEAD_CHOSEN_REQUEST_QUEST)
        session.database.grant_flag(session.character.id, UNDEAD_OPENING_COMPLETE_FLAG)
        await session.send(
            "\r\nOrra unwraps the smoked glass and fits it into the empty gate-lamp frame. 'Good timing.'\r\n"
            "The gate tender pauses, then adds, 'Tal asked, yes?'\r\n"
            "When you confirm it, Orra gives a satisfied nod. 'Good. We had enough orders down here for several civilizations.'\r\n"
            "The repaired lamp catches the desert light without glare. You helped because somebody asked and you decided the answer was yes. Nothing more mystical is required.\r\n"
            "\r\nQuest complete: A Request, Not an Order.\r\n"
            "Your reclamation opening is complete. The Sunscar Road lies EAST.\r\n"
        )
        return True

    return False


def _sentinel_target(target_text: str) -> bool:
    normalized = target_text.strip().lower()
    return normalized in {"sentinel", "bound sentinel", "ossuary sentinel", "guardian", "bound guardian"}


def _record_sentinel_defeat(session) -> None:
    if session.character is None:
        return
    if _active_step(session, UNDEAD_REMAINING_ORDER_QUEST.key) != "fight_sentinel":
        return
    session.database.grant_flag(session.character.id, UNDEAD_SENTINEL_DEFEATED_FLAG)
    session.database.advance_quest(session.character.id, UNDEAD_REMAINING_ORDER_QUEST.key, "break_sigil")


def _post_move_progress(session, destination_key: str) -> list[str]:
    """Advance room-arrival steps and return text for the runtime to send."""
    if session.character is None or session.character.race != "undead":
        return []
    lines: list[str] = []
    memory_step = _active_step(session, UNDEAD_MEMORY_QUEST.key)
    order_step = _active_step(session, UNDEAD_REMAINING_ORDER_QUEST.key)
    request_step = _active_step(session, UNDEAD_CHOSEN_REQUEST_QUEST.key)

    if destination_key == UNDEAD_FORMER_LIVES_ARCHIVE_KEY and memory_step == "reach_archive":
        session.database.advance_quest(session.character.id, UNDEAD_MEMORY_QUEST.key, "examine_effects")
        lines.append(
            "Archivist Mera looks up from a recovery box. 'These were found with you. They may be yours. They do not get to tell you who you are.'\r\nEXAMINE EFFECTS.\r\n"
        )
    elif destination_key == UNDEAD_COMMAND_VAULT_KEY and order_step == "reach_vault":
        session.database.advance_quest(session.character.id, UNDEAD_REMAINING_ORDER_QUEST.key, "fight_sentinel")
        lines.append(
            "The Bound Ossuary Sentinel completes one perfect turn and starts the same patrol again. Its master is gone. The order is not.\r\nATTACK SENTINEL.\r\n"
        )
    elif destination_key == UNDEAD_CHISEL_MARKET_KEY and request_step == "walk_market":
        session.database.grant_flag(session.character.id, UNDEAD_MARKET_SEEN_FLAG)
        session.database.advance_quest(session.character.id, UNDEAD_CHOSEN_REQUEST_QUEST.key, "meet_freehand")
        lines.append(
            "A bonewright complains about hinge prices while a potter complains about the bonewright. Somebody laughs. A reciter deliberately gives the wrong battle date just to provoke two scribes.\r\n"
            "This is not a tomb pretending to be a city. It is a city whose citizens happen to be dead. Continue SOUTH to Freehands Court and TALK TAL.\r\n"
        )
    elif destination_key == UNDEAD_SUNSCAR_ROAD_KEY and UNDEAD_OPENING_COMPLETE_FLAG in _flags(session) and UNDEAD_FIRST_OUTSIDE_FLAG not in _flags(session):
        session.database.grant_flag(session.character.id, UNDEAD_FIRST_OUTSIDE_FLAG)
        lines.append(
            "Behind you, the gate lamps become small against the black escarpment. Ahead, the road has no assigned destination.\r\n"
            "For most of your existence, purpose arrived as an order. Now the absence of an order is not a defect waiting to be repaired. It is room.\r\n"
        )
    return lines


def _movement_block_message(session, direction: str) -> str | None:
    if session.character is None or session.character.race != "undead":
        return None
    room = session.character.current_room
    no_voice_step = _active_step(session, UNDEAD_NO_VOICE_QUEST.key)
    memory = _quest(session, UNDEAD_MEMORY_QUEST.key)
    memory_active = bool(memory and memory.get("status") == "active")
    order = _quest(session, UNDEAD_REMAINING_ORDER_QUEST.key)
    order_active = bool(order and order.get("status") == "active")
    request = _quest(session, UNDEAD_CHOSEN_REQUEST_QUEST.key)
    request_step = _active_step(session, UNDEAD_CHOSEN_REQUEST_QUEST.key)

    if room == UNDEAD_START_ROOM_KEY:
        if direction == "south" and no_voice_step is not None:
            return "The civic lamps lead south, but Reclaimer Sevra stops you with an open palm. 'Free first. City second. Finish the severance check.'\r\n"
        if direction == "east" and no_voice_step in {"listen_silence", "talk_reclaimer"}:
            return "The severance hall is ready, but you have not yet established what—if anything—is still speaking inside you. LISTEN, then TALK RECLAIMER.\r\n"
    if room == UNDEAD_CONCOURSE_KEY:
        if direction in {"east", "down"} and memory_active:
            return "The wider Necropolis is not forbidden to you, but your recovery effects are waiting WEST in the Former Lives Archive. Finish that choice before taking on new work.\r\n"
        if direction == "down" and (order is None or order.get("status") != "active"):
            return "A guard chain blocks the stair to the old command vault. There is no reason to enter it yet.\r\n"
        if direction == "east" and order_active:
            return "The market can wait. The old command vault below is still part of your current reclamation work. Go DOWN.\r\n"
    if room == UNDEAD_CHISEL_MARKET_KEY and direction == "south" and request is None:
        return "Freehands Court is open, but you have not finished the old command-vault lesson yet.\r\n"
    if room == UNDEAD_DESERT_GATE_KEY and direction == "east" and UNDEAD_OPENING_COMPLETE_FLAG not in _flags(session):
        if request_step == "deliver_lamp":
            return "The road is physically open, but you chose to carry the lamp glass here. DELIVER LAMP before abandoning the request you accepted.\r\n"
        return "Your reclamation opening is still unfinished. The road will remain here when the current choice is actually yours.\r\n"
    return None


async def _delegate_prompt(self, previous_playing_prompt, command: str) -> None:
    had_instance_prompt = "prompt" in self.__dict__
    old_prompt = self.__dict__.get("prompt")

    async def replay_prompt(_text: str) -> str:
        return command

    self.prompt = replay_prompt
    try:
        await previous_playing_prompt(self)
    finally:
        if had_instance_prompt:
            self.prompt = old_prompt
        else:
            self.__dict__.pop("prompt", None)


def install_undead_runtime(player_session_class, world_service) -> None:
    install_undead_content(world_service)
    if getattr(player_session_class, "_undead_start_runtime_installed", False):
        return

    previous_enter_character = player_session_class.enter_character
    previous_playing_prompt = player_session_class.playing_prompt
    previous_enemy_lookup = player_session_class._enemy_in_current_room
    previous_finish_enemy = player_session_class._finish_enemy_defeat
    previous_move_character = player_session_class.move_character

    async def enter_character(self) -> None:
        if self.character is not None and self.character.race == "undead":
            prepare_undead_start(self)
        await previous_enter_character(self)
        if self.character is None or self.character.race != "undead":
            return
        if UNDEAD_OPENING_SEEN_FLAG not in _flags(self):
            self.database.grant_flag(self.character.id, UNDEAD_OPENING_SEEN_FLAG)
            await self.send(
                "\r\nThere should be a voice.\r\n"
                "Some buried part of you expects an order before movement: a word that tells the dead body what it is for. No word arrives.\r\n"
                "You wake on a basalt slab in the Reclamation Vault of the free Necropolis.\r\n"
                "New quest: No Voice Above You. LISTEN.\r\n"
            )
        definition, row = _current_opening_quest(self)
        if definition and row:
            objective = definition.objective_for_step(row.get("current_step"))
            if objective:
                await self.send(f"Reclamation objective: {objective}\r\n")

    async def move_character(self, direction: str) -> None:
        if self.character is not None and self.character.race == "undead":
            message = _movement_block_message(self, direction)
            if message:
                await self.send(message)
                return
            before = self.character.current_room
            await previous_move_character(self, direction)
            if self.character is None or self.character.race != "undead":
                return
            after = self.character.current_room
            if after and after != before:
                for text in _post_move_progress(self, after):
                    await self.send("\r\n" + text)
            return
        await previous_move_character(self, direction)

    def _enemy_in_current_room(self, target_text: str):
        if (
            self.character is not None
            and self.character.race == "undead"
            and self.character.current_room == UNDEAD_COMMAND_VAULT_KEY
            and _active_step(self, UNDEAD_REMAINING_ORDER_QUEST.key) == "fight_sentinel"
            and _sentinel_target(target_text)
        ):
            return EnemyState(BOUND_OSSUARY_SENTINEL)
        return previous_enemy_lookup(self, target_text)

    async def _finish_enemy_defeat(self, enemy) -> None:
        is_sentinel = (
            self.character is not None
            and self.character.race == "undead"
            and enemy.definition.key == UNDEAD_BOUND_SENTINEL_KEY
            and _active_step(self, UNDEAD_REMAINING_ORDER_QUEST.key) == "fight_sentinel"
        )
        await previous_finish_enemy(self, enemy)
        if not is_sentinel or self.character is None:
            return
        _record_sentinel_defeat(self)
        await self.send(
            "\r\nThe Bound Ossuary Sentinel collapses, its limbs still twitching toward the next patrol point. Defeat interrupted the body; it did not erase the order.\r\n"
            "The floor sigil continues to pulse. BREAK SIGIL.\r\n"
        )

    async def playing_prompt(self) -> None:
        if self.character is None or self.character.race != "undead":
            await previous_playing_prompt(self)
            return
        await self.send_client_state()
        command = await self.prompt("\r\n> ")
        if command is None:
            self.state = type(self.state).DISCONNECTED
            return
        normalized = command.strip().lower()

        if await handle_undead_start_command(self, command):
            return

        if normalized.startswith("attack ") or normalized.startswith("kill "):
            target = command.strip().split(maxsplit=1)[1]
            if _sentinel_target(target) and _active_step(self, UNDEAD_REMAINING_ORDER_QUEST.key) != "fight_sentinel":
                await self.send("\r\nThere is no active bound sentinel available to fight at this stage.\r\n")
                return

        await _delegate_prompt(self, previous_playing_prompt, command)
        if self.character is None or self.character.race != "undead":
            return
        if normalized in {"help", "?"}:
            await self.send(
                "Undead opening: use RECLAMATION or UNBOUND to review the current objective. The opening uses LISTEN, TALK RECLAIMER, EXAMINE BINDING, SEVER ORDERS, EXAMINE EFFECTS, TOUCH KEY, KEEP/DONATE/DESTROY KEY, ATTACK SENTINEL, BREAK SIGIL, TALK TAL, HELP TAL or DECLINE TAL, and possibly DELIVER LAMP.\r\n"
            )

    player_session_class.enter_character = enter_character
    player_session_class.move_character = move_character
    player_session_class.playing_prompt = playing_prompt
    player_session_class._enemy_in_current_room = _enemy_in_current_room
    player_session_class._finish_enemy_defeat = _finish_enemy_defeat
    player_session_class._undead_start_runtime_installed = True
