from __future__ import annotations

from dataclasses import dataclass

from mud.access import ContentGate


@dataclass(frozen=True, slots=True)
class QuestDefinition:
    key: str
    name: str
    style: str  # "structured" or "discovery"
    minimum_level: int = 1
    gate: ContentGate = ContentGate()
    description: str = ""
    objective_steps: tuple[tuple[str, str], ...] = ()

    def objective_for_step(self, step_key: str | None) -> str | None:
        if step_key is None:
            return None
        return dict(self.objective_steps).get(step_key)


@dataclass(frozen=True, slots=True)
class QuestDesignRules:
    early_game_uses_structured_guidance: bool = True
    world_also_supports_freeform_discovery: bool = True
    later_game_leans_more_on_exploration: bool = True
    structured_quests_are_not_the_only_progression_path: bool = True


QUEST_DESIGN_RULES = QuestDesignRules()

HUMAN_CATHEDRAL_SUMMONS = QuestDefinition(
    key="human_cathedral_summons",
    name="A Summons to the Cathedral",
    style="structured",
    description=(
        "A sealed note directs you through the Human capital to a senior cleric in the great cathedral. "
        "The short journey serves as the Human character's first guided introduction to navigation and quests."
    ),
    objective_steps=(
        ("read_note", "Read the Sealed Cathedral Note in your inventory."),
        ("find_cathedral", "Follow the city streets to the Grand Cathedral and speak with the High Acolyte."),
        ("complete", "You have answered the cathedral summons."),
    ),
)

HUMAN_COMBAT_TRAINING = QuestDefinition(
    key="human_combat_training",
    name="Lessons Beyond the Gate",
    style="structured",
    description=(
        "The High Acolyte marks the reverse of your cathedral note with directions to the Human training grounds. "
        "The exercise introduces targeting, real-time auto-attacks, class abilities, and fighting a creature that can retaliate."
    ),
    objective_steps=(
        ("read_training_orders", "Read the reverse of your Cathedral Note for the High Acolyte's training instructions."),
        ("reach_training_yard", "Leave through the Demon Gate and find the Training Yard outside the city wall."),
        ("practice_dummy", "Enter the Practice Ring and defeat a Training Dummy with ATTACK DUMMY."),
        ("defeat_vermin", "Enter the Vermin Pens and defeat either a Sewer Rat or Small Imp."),
        ("complete", "You completed the Human combat exercises."),
    ),
)


HUMAN_LOWER_WARDS_INVESTIGATION = QuestDefinition(
    key="human_lower_wards_investigation",
    name="Marks in the Ash",
    style="structured",
    description=(
        "After the Human combat lessons, the High Acolyte sends the character into the Lower Wards to investigate whispered disturbances. "
        "A partially erased occult mark links the ward to the secret signs around Cathedral Square and leads to a local informant with knowledge of the old cistern tunnels."
    ),
    objective_steps=(
        ("find_lower_wards", "Descend west from Ashen Way into the Lower Wards and look for the disturbance the High Acolyte described."),
        ("inspect_mark", "Find the sealed Blackglass Arch in the Lower Wards and EXAMINE MARK."),
        ("find_informant", "Find someone in the Lower Wards who recognizes the mark. Try TALK INFORMANT when you find the right person."),
        ("complete", "You learned that the mark signals an open way into old cistern tunnels beneath the city."),
    ),
)

FOREST_ELF_FIRST_WALK = QuestDefinition(
    key="forest_elf_first_walk",
    name="The Old River Path",
    style="structured",
    description=(
        "The local Druidic Circle sends a new Elf beyond the comfort of the town to learn the nearby forest through patient observation. "
        "The walk introduces exploration, environmental examination, and the slight natural magic woven through Elven life."
    ),
    objective_steps=(
        ("leave_clearing", "Leave Circle Clearing to the north and find the old river path."),
        ("follow_river", "Follow the Greenway east until you reach the Old River Path, then continue north beside the water."),
        ("study_waystone", "At Waystone Bend, EXAMINE WAYSTONE and learn what the Circle left for you."),
        ("listen_pool", "Continue east to the Listening Pool and LISTEN before going farther."),
        ("reach_outer_grove", "Follow the trail north to the Outer Grove and learn where the comfortable forest begins to end."),
        ("complete", "You completed the Druidic Circle's first walk beyond the town."),
    ),
)


SPOREKIN_FIRST_CALL = QuestDefinition(
    key="sporekin_first_call",
    name="The Chorus Beneath",
    style="structured",
    description=(
        "The Sporekin shared consciousness reaches the newly awakened character without speech, "
        "guiding them through the luminous underways toward the veiled edge of the surface world."
    ),
    objective_steps=(
        ("follow_living_threads", "Follow the living mycelial threads north from Lumen Hollow."),
        ("follow_cool_air", "In the Mycelial Gallery, follow the cooler moving air east toward the Rootwell."),
        ("climb_toward_light", "Climb up through Rootwell Ascent toward the pale natural light."),
        ("complete", "You answered the first call of the shared consciousness and reached the Veiled Grotto."),
    ),
)

SPOREKIN_FORGOTTEN_PULSE = QuestDefinition(
    key="sporekin_forgotten_pulse",
    name="The Forgotten Pulse",
    style="structured",
    description=(
        "Beyond the Veiled Grotto, the shared consciousness senses an old memory still echoing near the surface. "
        "A forgotten grove holds a ring of bioluminescent mushrooms whose pulse can be restored by touch."
    ),
    objective_steps=(
        ("cross_veil", "Pass north through the Veiled Grotto and follow the shared consciousness onto the surface."),
        ("find_grove", "Follow the faint remembered pulse east into the forgotten grove."),
        ("study_ring", "Examine the ancient mushroom ring and the stone at its center for a clue."),
        ("touch_blue", "Reproduce the remembered pulse by touching the mushrooms in the correct order."),
        ("touch_amber", "Reproduce the remembered pulse by touching the mushrooms in the correct order."),
        ("touch_violet", "Reproduce the remembered pulse by touching the mushrooms in the correct order."),
        ("touch_ivory", "Reproduce the remembered pulse by touching the mushrooms in the correct order."),
        ("complete", "You restored the forgotten pulse and revealed the old Sporekin path."),
    ),
)

QUESTS: tuple[QuestDefinition, ...] = (
    HUMAN_CATHEDRAL_SUMMONS, HUMAN_COMBAT_TRAINING, HUMAN_LOWER_WARDS_INVESTIGATION, FOREST_ELF_FIRST_WALK,
    SPOREKIN_FIRST_CALL, SPOREKIN_FORGOTTEN_PULSE
)
QUESTS_BY_KEY = {quest.key: quest for quest in QUESTS}
