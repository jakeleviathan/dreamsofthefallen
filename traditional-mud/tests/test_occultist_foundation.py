from mud.character_options import CLASSES_BY_KEY
from mud.class_progression import CLASS_ROLE_SUMMARIES, OCCULTIST_ABILITIES


def test_occultist_is_playable_class_option():
    occultist = CLASSES_BY_KEY["occultist"]
    assert occultist.name == "Occultist"
    assert "Strain" in occultist.class_passives
    assert "Veil-Sight" in occultist.class_passives


def test_occultist_has_authored_early_ladder():
    assert "occultist" in CLASS_ROLE_SUMMARIES
    assert [ability.unlock_level for ability in OCCULTIST_ABILITIES] == [1, 3, 5, 7, 9]
    assert {ability.key for ability in OCCULTIST_ABILITIES} == {
        "unmake", "borrowed_vitality", "wrong_step", "open_the_veil", "black_geometry"
    }
