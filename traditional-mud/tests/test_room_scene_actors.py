from __future__ import annotations

import asyncio
from dataclasses import dataclass
from types import SimpleNamespace

import mud.crafting as crafting
import mud.room_scene_actors as scenes
from mud.database import Database
from mud.sols import merchant_buyback_price


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


def test_scene_targets_accept_natural_look_aliases():
    assert scenes._target_matches("at wildflower", "wildflowers", "Wildflowers")
    assert scenes._target_matches("blood", "blood:wolf", "Pool of Blood", "blood")


def test_picking_wildflowers_creates_inventory_and_depletes_local_patch(tmp_path, monkeypatch):
    database = Database(tmp_path / "flora.db")
    account = database.create_account("flora_account", "hash")
    character = database.create_character(account.id, "Forager", "human", "druid")

    class EcologyState:
        vegetation = 0.9
        resource_stock = 0.9

    ecology_state = EcologyState()
    monkeypatch.setattr(scenes.ASTRALIS_ECOLOGY, "state_for", lambda _region: ecology_state)
    monkeypatch.setattr(scenes.ASTRALIS_ECOLOGY, "_write", lambda _region, _state: None)
    monkeypatch.setattr(
        scenes.ASTRALIS_ECOLOGY,
        "_region_biomes",
        {"flora_region": "temperate grassland"},
    )

    class Session:
        def __init__(self):
            self.database = database
            self.character = SimpleNamespace(id=character.id, current_room="flora_room")
            self.outputs = []

        async def send(self, text):
            self.outputs.append(text)

    class World:
        def scene(self, room_key):
            if room_key != "flora_room":
                return None
            return SimpleNamespace(key="flora_room", region_key="flora_region")

    session = Session()
    world = World()

    for _ in range(scenes.FLORA_DAILY_PICK_LIMIT):
        assert asyncio.run(scenes._handle_flora(session, world, "pick", "flowers")) is True

    assert database.item_quantity(character.id, "wildflower") == scenes.FLORA_DAILY_PICK_LIMIT
    assert "add it to your inventory" in "".join(session.outputs)
    assert scenes._flora_picked_today(
        database,
        "flora_room",
        "wildflowers",
        scenes.ASTRALIS_CLOCK.now().day_number,
    ) == scenes.FLORA_DAILY_PICK_LIMIT

    before = database.item_quantity(character.id, "wildflower")
    assert asyncio.run(scenes._handle_flora(session, world, "pick", "flowers")) is True
    assert database.item_quantity(character.id, "wildflower") == before
    assert "picked enough for today" in session.outputs[-1]


def test_ambient_flora_items_are_registered_but_not_vendor_fodder():
    for item_key in ("wildflower", "marsh_bloom", "glowcap"):
        assert item_key in crafting.ITEMS_BY_KEY
        assert crafting.ITEMS_BY_KEY[item_key].category == "flora"
        assert merchant_buyback_price(item_key) == 0
