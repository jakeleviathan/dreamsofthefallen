from __future__ import annotations

import asyncio
import unittest
from types import SimpleNamespace

import mud.combat as combat
import mud.world as world
from mud.goblin_outer_route import GOBLIN_FIRST_PILING_KEY, GOBLIN_OUTER_ROUTE_COMPLETE_FLAG
from mud.goblin_start import GOBLIN_REGION_KEY, goblin_room_augmentations, install_goblin_world
from mud.goblin_swamp import (
    BOG_SNAPPER,
    GOBLIN_APOTHECARY_BLIND_KEY,
    GOBLIN_BITTERWATER_RUN_KEY,
    GOBLIN_CLEANWATER_SEEP_KEY,
    GOBLIN_LANTERNMOSS_CUT_KEY,
    GOBLIN_MUDGLASS_CROSSING_KEY,
    GOBLIN_REEDFEN_CAUSEWAY_KEY,
    GOBLIN_ROOTSNAG_BANK_KEY,
    GOBLIN_SWAMP_GATHERING,
    GOBLIN_SWAMP_ROOM_KEYS,
    MIRE_TICK_SWARM,
    PELLA_MIREGLASS,
    _handle_alchemy,
    _handle_swamp_gathering,
    install_goblin_swamp_content,
)
from mud.goblin_swamp_access import enforce_first_piling_swamp_access
from mud.room_engine import PlayerRoomContext, WorldService


class FakeDatabase:
    def __init__(self) -> None:
        self.items: dict[tuple[int, str], int] = {}
        self.skills: dict[tuple[int, str], int] = {}
        self.flags: set[tuple[int, str]] = set()

    def item_quantity(self, character_id: int, item_key: str) -> int:
        return self.items.get((character_id, item_key), 0)

    def add_item(self, character_id: int, item_key: str, quantity: int = 1) -> None:
        key = (character_id, item_key)
        self.items[key] = self.items.get(key, 0) + quantity

    def get_trade_skill_progress(self, character_id: int, trade_skill_key: str):
        return {"uses": self.skills.get((character_id, trade_skill_key), 0), "skill_xp": self.skills.get((character_id, trade_skill_key), 0)}

    def record_trade_skill_use(self, character_id: int, trade_skill_key: str, skill_xp_gain: int = 1) -> None:
        key = (character_id, trade_skill_key)
        self.skills[key] = self.skills.get(key, 0) + skill_xp_gain

    def complete_crafting_transaction(
        self,
        character_id: int,
        *,
        trade_skill_key: str,
        materials,
        output_item_key: str,
        output_quantity: int = 1,
        skill_xp_gain: int = 1,
    ) -> bool:
        for requirement in materials:
            if self.item_quantity(character_id, requirement.item_key) < requirement.quantity:
                return False
        for requirement in materials:
            key = (character_id, requirement.item_key)
            self.items[key] -= requirement.quantity
        self.add_item(character_id, output_item_key, output_quantity)
        self.record_trade_skill_use(character_id, trade_skill_key, skill_xp_gain)
        return True

    def list_flags(self, character_id: int):
        return frozenset(flag for owner, flag in self.flags if owner == character_id)

    def grant_flag(self, character_id: int, flag_key: str) -> None:
        self.flags.add((character_id, flag_key))


class FakeSession:
    def __init__(self, room_key: str, race: str = "goblin") -> None:
        self.character = SimpleNamespace(id=701, name="Nib", race=race, current_room=room_key)
        self.database = FakeDatabase()
        self.outputs: list[str] = []

    async def send(self, text: str) -> None:
        self.outputs.append(text)


class GoblinSwampTests(unittest.TestCase):
    def setUp(self) -> None:
        self.rooms = world.ROOMS
        self.rooms_by_key = dict(world.ROOMS_BY_KEY)
        self.npcs = world.NPCS
        self.npcs_by_key = dict(world.NPCS_BY_KEY)
        self.enemies = combat.ENEMIES
        self.enemies_by_key = dict(combat.ENEMIES_BY_KEY)
        install_goblin_world()
        GOBLIN_SWAMP_GATHERING.reset()

    def tearDown(self) -> None:
        world.ROOMS = self.rooms
        world.ROOMS_BY_KEY.clear()
        world.ROOMS_BY_KEY.update(self.rooms_by_key)
        world.NPCS = self.npcs
        world.NPCS_BY_KEY.clear()
        world.NPCS_BY_KEY.update(self.npcs_by_key)
        combat.ENEMIES = self.enemies
        combat.ENEMIES_BY_KEY.clear()
        combat.ENEMIES_BY_KEY.update(self.enemies_by_key)
        GOBLIN_SWAMP_GATHERING.reset()

    def _service(self) -> WorldService:
        service = WorldService(rooms=world.ROOMS_BY_KEY, augmentations=goblin_room_augmentations())
        install_goblin_swamp_content(service)
        enforce_first_piling_swamp_access(service)
        return service

    def test_swamp_adds_branching_beginner_network(self) -> None:
        self._service()
        self.assertEqual(len(GOBLIN_SWAMP_ROOM_KEYS), 7)
        for room_key in GOBLIN_SWAMP_ROOM_KEYS:
            room = world.ROOMS_BY_KEY[room_key]
            self.assertEqual(room.region_key, GOBLIN_REGION_KEY)
            self.assertIn("goblin_newbie_swamp", room.tags)
            self.assertIn("beginner_wilderness", room.tags)

        first_piling = world.ROOMS_BY_KEY[GOBLIN_FIRST_PILING_KEY]
        self.assertEqual(first_piling.exits["north"], GOBLIN_REEDFEN_CAUSEWAY_KEY)
        self.assertEqual(first_piling.exits["east"], GOBLIN_BITTERWATER_RUN_KEY)
        self.assertEqual(first_piling.exits["west"], GOBLIN_LANTERNMOSS_CUT_KEY)

        self.assertEqual(
            world.ROOMS_BY_KEY[GOBLIN_MUDGLASS_CROSSING_KEY].exits,
            {
                "south": GOBLIN_REEDFEN_CAUSEWAY_KEY,
                "east": GOBLIN_ROOTSNAG_BANK_KEY,
                "west": GOBLIN_APOTHECARY_BLIND_KEY,
            },
        )
        self.assertEqual(
            world.ROOMS_BY_KEY[GOBLIN_CLEANWATER_SEEP_KEY].exits,
            {"west": GOBLIN_REEDFEN_CAUSEWAY_KEY},
        )

    def test_first_piling_branches_open_only_after_first_route_lesson(self) -> None:
        service = self._service()
        locked = PlayerRoomContext(character_id=1, race_key="goblin", class_key="brute", level=1)
        unlocked = PlayerRoomContext(
            character_id=1,
            race_key="goblin",
            class_key="brute",
            level=1,
            character_flags=frozenset({GOBLIN_OUTER_ROUTE_COMPLETE_FLAG}),
        )
        locked_view = service.build_view(GOBLIN_FIRST_PILING_KEY, locked)
        unlocked_view = service.build_view(GOBLIN_FIRST_PILING_KEY, unlocked)
        self.assertEqual({value.direction for value in locked_view.exits}, {"south"})
        self.assertEqual(
            {value.direction for value in unlocked_view.exits},
            {"south", "north", "east", "west"},
        )

    def test_beginner_wildlife_is_light_and_optional_static_combat(self) -> None:
        self._service()
        self.assertLessEqual(MIRE_TICK_SWARM.auto_attack_damage, 1)
        self.assertLessEqual(BOG_SNAPPER.auto_attack_damage, 2)
        self.assertLessEqual(MIRE_TICK_SWARM.max_hp, 14)
        self.assertLessEqual(BOG_SNAPPER.max_hp, 22)
        self.assertEqual(world.ROOMS_BY_KEY[GOBLIN_MUDGLASS_CROSSING_KEY].enemy_keys, (MIRE_TICK_SWARM.key,))
        self.assertEqual(world.ROOMS_BY_KEY[GOBLIN_ROOTSNAG_BANK_KEY].enemy_keys, (BOG_SNAPPER.key,))
        for room_key in GOBLIN_SWAMP_ROOM_KEYS:
            self.assertLessEqual(len(world.ROOMS_BY_KEY[room_key].enemy_keys), 1)

    def test_goblin_field_apothecary_is_authored_as_public_route_infrastructure(self) -> None:
        self._service()
        room = world.ROOMS_BY_KEY[GOBLIN_APOTHECARY_BLIND_KEY]
        self.assertIn("alchemy_station", room.tags)
        self.assertIn("mortar_and_pestle", room.tags)
        self.assertIn("alchemy_table", room.tags)
        self.assertIn(PELLA_MIREGLASS.key, room.npc_keys)
        self.assertIs(world.NPCS_BY_KEY[PELLA_MIREGLASS.key], PELLA_MIREGLASS)

    def test_greenleaf_trains_herbalism_until_bitterroot_is_available(self) -> None:
        session = FakeSession(GOBLIN_REEDFEN_CAUSEWAY_KEY)

        for _ in range(3):
            handled = asyncio.run(_handle_swamp_gathering(session, "gather greenleaf"))
            self.assertTrue(handled)
        self.assertEqual(session.database.item_quantity(701, "greenleaf"), 3)
        self.assertEqual(session.database.get_trade_skill_progress(701, "herbalism")["skill_xp"], 3)

        session.character.current_room = GOBLIN_LANTERNMOSS_CUT_KEY
        for _ in range(2):
            asyncio.run(_handle_swamp_gathering(session, "gather greenleaf"))
        self.assertEqual(session.database.get_trade_skill_progress(701, "herbalism")["skill_xp"], 5)

        session.character.current_room = GOBLIN_BITTERWATER_RUN_KEY
        handled = asyncio.run(_handle_swamp_gathering(session, "gather bitterroot"))
        self.assertTrue(handled)
        self.assertEqual(session.database.item_quantity(701, "bitterroot"), 1)
        self.assertEqual(session.database.get_trade_skill_progress(701, "herbalism")["skill_xp"], 6)

    def test_bitterroot_explains_skill_gate_instead_of_failing_silently(self) -> None:
        session = FakeSession(GOBLIN_BITTERWATER_RUN_KEY)
        handled = asyncio.run(_handle_swamp_gathering(session, "gather bitterroot"))
        self.assertTrue(handled)
        self.assertEqual(session.database.item_quantity(701, "bitterroot"), 0)
        self.assertTrue(any("requires herbalism skill 5" in text.lower() for text in session.outputs))

    def test_swamp_ingredients_can_make_real_beginner_potion_at_field_bench(self) -> None:
        session = FakeSession(GOBLIN_REEDFEN_CAUSEWAY_KEY)
        asyncio.run(_handle_swamp_gathering(session, "gather greenleaf"))
        asyncio.run(_handle_swamp_gathering(session, "gather greenleaf"))

        session.character.current_room = GOBLIN_CLEANWATER_SEEP_KEY
        handled = asyncio.run(_handle_swamp_gathering(session, "collect water"))
        self.assertTrue(handled)
        self.assertEqual(session.database.item_quantity(701, "spring_water"), 1)

        session.character.current_room = GOBLIN_APOTHECARY_BLIND_KEY
        handled = asyncio.run(_handle_alchemy(session, "brew minor healing potion"))
        self.assertTrue(handled)
        self.assertEqual(session.database.item_quantity(701, "minor_healing_potion"), 1)
        self.assertEqual(session.database.item_quantity(701, "greenleaf"), 0)
        self.assertEqual(session.database.item_quantity(701, "spring_water"), 0)
        self.assertEqual(session.database.get_trade_skill_progress(701, "alchemy")["skill_xp"], 1)
        self.assertTrue(any("Minor Healing Potion" in text for text in session.outputs))

    def test_field_alchemy_is_culturally_goblin_but_not_race_locked(self) -> None:
        session = FakeSession(GOBLIN_APOTHECARY_BLIND_KEY, race="human")
        session.database.add_item(701, "greenleaf", 2)
        session.database.add_item(701, "spring_water", 1)
        handled = asyncio.run(_handle_alchemy(session, "brew minor healing potion"))
        self.assertTrue(handled)
        self.assertEqual(session.database.item_quantity(701, "minor_healing_potion"), 1)


if __name__ == "__main__":
    unittest.main()
