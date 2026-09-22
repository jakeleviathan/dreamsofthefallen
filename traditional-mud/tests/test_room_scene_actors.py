from __future__ import annotations

from dataclasses import dataclass

import mud.room_scene_actors as scenes


@dataclass
class FakeDB:
    pass


def test_weather_decay_factor_accelerates_exposed_traces():
    assert scenes._weather_decay_factor("heavy rain") < scenes._weather_decay_factor("clear")


def test_nonliving_enemies_do_not_bleed():
    assert scenes.record_combat_trace(FakeDB(), "room", "bone_skeleton", "Bone Skeleton", roll=0.0) is False


def test_blood_is_rare_not_guaranteed():
    assert scenes.record_combat_trace(FakeDB(), "room", "wolf", "Wolf", roll=0.99) is False


def test_ecology_flora_requires_healthy_growth(monkeypatch):
    class State:
        vegetation = 0.2
        resource_stock = 0.9
    monkeypatch.setattr(scenes.ASTRALIS_ECOLOGY, "state_for", lambda _region: State())
    assert scenes._ecology_flora("room", "region") == ()
