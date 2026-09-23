from mud.trademark_moments import TrademarkContext, TrademarkMoment, choose_trademark_moment, eligible_moments


def test_occultist_sees_class_moment():
    context = TrademarkContext(event="enter_room", character_class="occultist", race="human", level=5, room_tags=frozenset({"settlement"}))
    keys = {m.key for m in eligible_moments(context)}
    assert "occultist_extra_shadow" in keys


def test_race_and_class_combo_is_more_specific():
    context = TrademarkContext(event="examine", character_class="priest", race="goblin", level=6)
    moment = choose_trademark_moment(context)
    assert moment is not None
    assert moment.key == "goblin_priest_junk_reliquary"


def test_once_moment_respects_history_flag():
    moment = TrademarkMoment("test_once", "enter_room", "hello")
    context = TrademarkContext(event="enter_room", character_class="brute", race="human", level=1, flags=frozenset({moment.flag_key}))
    assert eligible_moments(context, (moment,)) == ()


def test_context_requirements_are_enforced():
    moment = TrademarkMoment("rain_road", "weather_change", "rain", room_tags=("road",), weather=("rain",))
    dry = TrademarkContext(event="weather_change", character_class="druid", race="forest_elf", level=3, room_tags=frozenset({"road"}), weather="clear")
    wet = TrademarkContext(event="weather_change", character_class="druid", race="forest_elf", level=3, room_tags=frozenset({"road"}), weather="rain")
    assert choose_trademark_moment(dry, (moment,)) is None
    assert choose_trademark_moment(wet, (moment,)) == moment
