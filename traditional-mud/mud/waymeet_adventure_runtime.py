from __future__ import annotations

import mud.economy_loop as economy
import mud.waymeet_adventure_arc as arc
from mud.room_engine import ExitDefinition, FeatureDefinition, RoomAugmentation, ViewCondition


def _feature(key: str, name: str, summary: str, examine: str, aliases: tuple[str, ...] = ()) -> FeatureDefinition:
    return FeatureDefinition(
        key=key,
        name=name,
        aliases=aliases,
        summary=summary,
        examine_text=examine,
    )


def corrected_adventure_augmentations() -> dict[str, RoomAugmentation]:
    """Build the adventure exits with explicit keyword arguments.

    The main content module stays intentionally data-heavy; this installer keeps
    the room-engine call surface explicit so future field additions cannot shift
    positional arguments and silently open gated routes.
    """
    return {
        arc.WAYMEET_BROKEN_MILE_KEY: RoomAugmentation(extra_exits=(
            ExitDefinition(
                direction="south", destination_key=arc.OLD_TOLL_ROAD,
                name="Old Toll Road", travel_text="You follow the older road south toward a roofless tollhouse.",
                condition=ViewCondition(min_level=2), hidden_when_unavailable=True,
            ),
        )),
        arc.WAYMEET_BRIARCUT_KEY: RoomAugmentation(extra_exits=(
            ExitDefinition(
                direction="east", destination_key=arc.BRIARWOOD_EDGE,
                name="Briarwood Track", travel_text="You take the narrow east track beneath the briars.",
                condition=ViewCondition(min_level=3), hidden_when_unavailable=True,
            ),
        )),
        arc.WAYMEET_QUARRY_KEY: RoomAugmentation(extra_exits=(
            ExitDefinition(
                direction="north", destination_key=arc.KINGS_SCAR_APPROACH,
                name="King's Scar Track", travel_text="You follow old quarry stakes toward the larger cut in the hills.",
                condition=ViewCondition(min_level=5), hidden_when_unavailable=True,
            ),
        )),
        arc.WAYMEET_HIGH_ROAD_KEY: RoomAugmentation(extra_exits=(
            ExitDefinition(
                direction="east", destination_key=arc.ECHO_RIDGE,
                name="Echo Ridge", travel_text="You climb a bare side ridge where the wind returns footsteps strangely.",
                condition=ViewCondition(min_level=2), hidden_when_unavailable=True,
            ),
        )),
        arc.OLD_TOLL_ROAD: RoomAugmentation(
            extra_exits=(ExitDefinition(
                direction="down", destination_key=arc.TOLL_ENTRY,
                name="Tollhouse Cellar", travel_text="You descend through the newer cellar doors.",
                condition=ViewCondition(min_level=2), hidden_when_unavailable=True,
            ),),
            features=(_feature(
                "toll_cellar_doors", "Cellar Doors", "freshly repaired doors beneath a ruined tollhouse",
                "The doors are not locked. Fresh boot marks go down. DOWN enters the first compact dungeon.",
                ("doors", "cellar", "tollhouse"),
            ),),
        ),
        arc.BRIARWOOD_EDGE: RoomAugmentation(
            extra_exits=(ExitDefinition(
                direction="north", destination_key=arc.BELL_GATE,
                name="Crooked Bell Chapel", travel_text="You push north through the briars toward the cracked bell.",
                condition=ViewCondition(min_level=3), hidden_when_unavailable=True,
            ),),
            features=(_feature(
                "crooked_bell_sound", "Crooked Bell", "one dull bell-note arriving at the wrong interval",
                "The bell is north. This dungeon rewards LISTEN before PULL.",
                ("bell", "sound", "chapel"),
            ),),
        ),
        arc.KINGS_SCAR_APPROACH: RoomAugmentation(
            extra_exits=(ExitDefinition(
                direction="east", destination_key=arc.SCAR_GATE,
                name="King's Scar Quarry", travel_text="You pass the survey flags into the abandoned quarry.",
                condition=ViewCondition(min_level=5), hidden_when_unavailable=True,
            ),),
            features=(_feature(
                "scar_survey_flags", "Survey Flags", "fresh Dwarven flags marking the safer quarry line",
                "The flags repeatedly mark the old lift house. TALK BRIN before committing to the deeper cut.",
                ("flags", "survey", "quarry"),
            ),),
        ),
        arc.ECHO_RIDGE: RoomAugmentation(
            extra_exits=(ExitDefinition(
                direction="down", destination_key=arc.ECHO_THRESHOLD,
                name="Vault Stair",
                travel_text="The three marks answer together and a seam in the ridge opens onto a descending stair.",
                condition=ViewCondition(
                    required_flags=(arc.TOLL_COMPLETE, arc.BELL_COMPLETE, arc.SCAR_COMPLETE),
                    min_level=8,
                ),
                hidden_when_unavailable=True,
            ),),
            features=(_feature(
                "echo_ridge_marks", "Three Listening Marks", "three old marks that return footsteps with an extra answer",
                "Three early expeditions elsewhere around Waymeet contain matching marks. The ridge opens only after all three dungeon clears and level 8.",
                ("marks", "echo marks", "listening marks"),
            ),),
        ),
        arc.TOLL_LEDGER: RoomAugmentation(features=(_feature(
            "recent_ledger", "Recent Ledger", "a thief's ledger naming stolen wagons and payments",
            "SEARCH LEDGER to compare entries and identify who is running the cellar.",
            ("ledger", "book", "accounts"),
        ),)),
        arc.TOLL_COUNTING: RoomAugmentation(
            extra_exits=(ExitDefinition(
                direction="down", destination_key=arc.TOLL_HIDDEN_STAIR,
                name="Hidden Stair", travel_text="You squeeze through the newly exposed wall seam and descend.",
                condition=ViewCondition(required_flags=(arc.TOLL_STAIR_FOUND,), min_level=2),
                hidden_when_unavailable=True,
            ),),
            features=(_feature(
                "clean_wall", "Clean Wall", "one suspiciously clean cellar wall",
                "After Tollmaster Vesk is down, SEARCH WALL can reveal whether the clean stone hides anything.",
                ("wall", "clean wall", "stone"),
            ),),
        ),
        arc.TOLL_CARVED_SUBLEVEL: RoomAugmentation(features=(_feature(
            "carved_wall", "Carved Wall", "wave-like lines surrounding one open shape",
            "EXAMINE CARVED WALL. The pattern will matter much later, but the cellar itself does not explain it.",
            ("wall", "carving", "carved wall", "marks"),
        ),)),
        arc.BELL_NAVE: RoomAugmentation(features=(_feature(
            "three_pitches", "Three Returning Pitches", "rain notes repeating more regularly than rain should",
            "LISTEN. The game tells you the usable clue rather than asking you to guess an audio verb.",
            ("pitches", "rain", "sound"),
        ),)),
        arc.BELL_EAST_GALLERY: RoomAugmentation(features=(_feature(
            "bronze_plates", "Cracked Bronze Plates", "low, high, and low plates touched by wind",
            "LISTEN here after the nave. The rope order becomes explicit.",
            ("plates", "bronze plates", "sound"),
        ),)),
        arc.BELL_ROPE_ROOM: RoomAugmentation(
            extra_exits=(ExitDefinition(
                direction="up", destination_key=arc.BELL_BELFRY,
                name="Belfry Latch", travel_text="The solved rope latch releases and the upper door swings inward.",
                condition=ViewCondition(required_flags=(arc.BELL_ROPES_SOLVED,), min_level=3),
                hidden_when_unavailable=True,
            ),),
            features=(_feature(
                "bell_ropes", "Low and High Ropes", "two surviving bell-control ropes",
                "Use PULL LOW and PULL HIGH in the three-note sequence you heard. Wrong pulls reset the sequence without consuming anything.",
                ("ropes", "low rope", "high rope"),
            ),),
        ),
        arc.BELL_BELFRY: RoomAugmentation(
            extra_exits=(ExitDefinition(
                direction="up", destination_key=arc.BELL_ECHO_LOFT,
                name="Echo Loft", travel_text="You climb into the crawlspace above the bell.",
                condition=ViewCondition(required_flags=(arc.BELL_SECRET,), min_level=3),
                hidden_when_unavailable=True,
            ),),
            features=(_feature(
                "bell_rafters", "Split Rafters", "old rafters disappearing above the bell frame",
                "After the Bellkeeper falls, SEARCH RAFTERS may reveal a place the old caretaker used for listening tests.",
                ("rafters", "loft", "beams"),
            ),),
        ),
        arc.SCAR_LIFT: RoomAugmentation(features=(_feature(
            "inspection_gantry", "Inspection Gantry", "a narrow maintenance walk above the dead lift",
            "CLIMB GANTRY. The command demonstrates vertical exploration before the quarry asks you to rely on it.",
            ("gantry", "lift", "walk"),
        ),)),
        arc.SCAR_DEEP_FACE: RoomAugmentation(features=(_feature(
            "survey_marks", "Old Survey Marks", "a nearly erased cluster among newer chalk",
            "SEARCH SURVEY MARKS if you care about the older history. It is optional and gives no power reward.",
            ("marks", "survey marks", "chalk"),
        ),)),
        arc.SCAR_WINCH: RoomAugmentation(
            extra_exits=(ExitDefinition(
                direction="east", destination_key=arc.SCAR_BREAKER_PIT,
                name="Restored Freight Bridge",
                travel_text="The released brake lets the freight bridge settle across the gap to the breaker pit.",
                condition=ViewCondition(required_flags=(arc.SCAR_BRAKE_RELEASED,), min_level=5),
                hidden_when_unavailable=True,
            ),),
            features=(_feature(
                "freight_brake", "Freight Brake", "a rusted but intact geared brake lever",
                "PULL BRAKE to release the bridge. This is an environmental action, not a hidden parser trick.",
                ("brake", "lever", "winch"),
            ),),
        ),
        arc.ECHO_PLATE_WEST: RoomAugmentation(features=(_feature(
            "west_plate", "Resonance Plate", "a worn black plate", "TOUCH PLATE.",
            ("plate", "stone", "resonance plate"),
        ),)),
        arc.ECHO_PLATE_EAST: RoomAugmentation(features=(_feature(
            "east_plate", "Resonance Plate", "a ringed black plate", "TOUCH PLATE.",
            ("plate", "stone", "resonance plate"),
        ),)),
        arc.ECHO_PLATE_DEEP: RoomAugmentation(features=(_feature(
            "deep_plate", "Resonance Plate", "the deepest black plate", "TOUCH PLATE.",
            ("plate", "stone", "resonance plate"),
        ),)),
        arc.ECHO_MIRROR_CHOIR: RoomAugmentation(
            extra_exits=(
                ExitDefinition(
                    direction="east", destination_key=arc.ECHO_LISTENER_COURT,
                    name="Listener's Court",
                    travel_text="All three resonance plates answer and the black panels separate.",
                    condition=ViewCondition(required_flags=(arc.ECHO_GATE_OPEN,), min_level=8),
                    hidden_when_unavailable=True,
                ),
                ExitDefinition(
                    direction="south", destination_key=arc.ECHO_FIRST_BREATH_MARGIN,
                    name="Hidden Margin",
                    travel_text="The three optional marks align and a narrow margin opens in the wall.",
                    condition=ViewCondition(required_flags=(arc.DEEP_SECRET_OPEN,), min_level=8),
                    hidden_when_unavailable=True,
                ),
            ),
            features=(_feature(
                "three_secret_marks", "Three Tiny Marks", "three tiny signs matching optional discoveries elsewhere",
                "If you found all three outer secrets, TOUCH THREE MARKS here. Otherwise the marks remain inert and unexplained.",
                ("marks", "three marks", "tiny marks"),
            ),),
        ),
        arc.ECHO_LISTENER_COURT: RoomAugmentation(features=(_feature(
            "resonator_chains", "Resonator Chains", "four chains at the corners of the court",
            "If the Listener begins imitating a breath, LISTEN first. When you understand the false rhythm, PULL RESONATOR to collapse it.",
            ("chains", "resonator", "resonators"),
        ),)),
    }


def install_waymeet_adventure_runtime(player_session_class, world_service) -> None:
    """Install the adventure arc with two compatibility guards kept local.

    The base economy LootDrop type is intentionally simple and does not model
    probabilities. The authored arc originally expresses a few flavor drops with
    a chance keyword, so installation temporarily accepts that keyword while
    preserving the existing deterministic LootDrop object and restores the
    original constructor immediately afterward.
    """
    if getattr(player_session_class, "_waymeet_adventure_runtime_installed", False):
        return

    arc.adventure_augmentations = corrected_adventure_augmentations
    original_loot_drop = economy.LootDrop

    def compatible_loot_drop(item_key: str, quantity: int = 1, chance: float | None = None):
        # Current economy tables are deterministic. The chance annotation is
        # retained as authoring intent for a later probabilistic-loot pass; for
        # now the item simply participates in the ordinary table.
        return original_loot_drop(item_key, quantity)

    economy.LootDrop = compatible_loot_drop
    original_engage = arc._engage_boss

    async def hardened_engage(session, definition):
        if definition.key == arc.LISTENER_BELOW.key:
            session._listener_breath_triggered = False
        return await original_engage(session, definition)

    arc._engage_boss = hardened_engage
    try:
        arc.install_waymeet_adventure_runtime(player_session_class, world_service)
    finally:
        economy.LootDrop = original_loot_drop
