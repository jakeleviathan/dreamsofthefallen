from __future__ import annotations

import asyncio
import unittest
from types import SimpleNamespace

from mud.unblinking_star_observatory import (
    APERTURE_SEALED_FLAG,
    BOSS_DEFEATED_FLAG,
    CORE_GATE_FLAG,
    LENSES_ALIGNED_FLAG,
    OBS_APERTURE_KEY,
    OBS_LENS_GALLERY_KEY,
    OBS_NULL_ORRERY_KEY,
    OBS_SEAL_ENGINE_KEY,
    OBS_THREE_HAND_GATE_KEY,
    OBSERVATORY_ROOM_KEYS,
    OPEN_EYED_FRAGMENT,
    ORRERY_ALIGNED_FLAG,
    QUEST_KEY,
    STARFALL_ROOM_KEYS,
    UNBLINKING_QUEST,
    UNBLINKING_ROOMS,
    _align_lens,
    _seal_aperture,
    _synchronize_gate,
    _turn_orrery,
    unblinking_augmentations,
)


class _FakeDatabase:
    def __init__(self) -> None:
        self.flags: dict[int, set[str]] = {}
        self.quests: dict[int, dict] = {}
        self.items: dict[tuple[int, str], int] = {}
        self.xp: dict[int, int] = {}

    def list_flags(self, character_id: int):
        return tuple(self.flags.get(character_id, set()))

    def grant_flag(self, character_id: int, flag: str) -> None:
        self.flags.setdefault(character_id, set()).add(flag)

    def revoke_flag(self, character_id: int, flag: str) -> None:
        self.flags.setdefault(character_id, set()).discard(flag)

    def get_quest(self, character_id: int, quest_key: str):
        if quest_key != QUEST_KEY:
            return None
        return self.quests.get(character_id)

    def advance_quest(self, character_id: int, quest_key: str, next_step: str) -> None:
        assert quest_key == QUEST_KEY
        self.quests[character_id]["current_step"] = next_step

    def add_item(self, character_id: int, item_key: str, quantity: int = 1) -> None:
        key = (character_id, item_key)
        self.items[key] = self.items.get(key, 0) + quantity

    def add_experience(self, character_id: int, amount: int):
        self.xp[character_id] = self.xp.get(character_id, 0) + amount
        return 15

    def get_character_by_name(self, _name: str):
        return None


class _Session:
    def __init__(self, database: _FakeDatabase, character_id: int, room_key: str) -> None:
        self.database = database
        self.character = SimpleNamespace(
            id=character_id,
            name=f"Observer{character_id}",
            level=15,
            current_room=room_key,
        )
        self.sent: list[str] = []
        self.party: list[_Session] = []

    def party_sessions_here(self):
        return [member for member in self.party if member.character.current_room == self.character.current_room]

    async def send(self, text: str) -> None:
        self.sent.append(text)


class UnblinkingStarContentTests(unittest.TestCase):
    def test_new_region_is_a_substantial_29_room_adventure(self):
        self.assertEqual(len(STARFALL_ROOM_KEYS), 10)
        self.assertEqual(len(OBSERVATORY_ROOM_KEYS), 19)
        self.assertEqual(len(UNBLINKING_ROOMS), 29)
        self.assertEqual(len({room.key for room in UNBLINKING_ROOMS}), 29)

    def test_quest_preserves_level_13_to_16_group_shape(self):
        self.assertEqual(UNBLINKING_QUEST.minimum_level, 13)
        steps = dict(UNBLINKING_QUEST.objective_steps)
        self.assertIn("align_lenses", steps)
        self.assertIn("sync_gate", steps)
        self.assertIn("align_orrery", steps)
        self.assertIn("defeat_fragment", steps)
        self.assertIn("seal_aperture", steps)
        self.assertIn("three party members", steps["align_lenses"].lower())
        self.assertIn("level-15", steps["defeat_fragment"].lower())

    def test_deep_gate_and_seal_engine_are_flag_gated(self):
        augmentations = unblinking_augmentations()
        gate_exit = augmentations[OBS_THREE_HAND_GATE_KEY].exit_overrides[0]
        seal_exit = augmentations[OBS_APERTURE_KEY].exit_overrides[0]
        self.assertEqual(gate_exit.destination_key, "unblinking_inversion_stair")
        self.assertEqual(gate_exit.condition.required_flags, (CORE_GATE_FLAG,))
        self.assertEqual(seal_exit.destination_key, OBS_SEAL_ENGINE_KEY)
        self.assertEqual(seal_exit.condition.required_flags, (BOSS_DEFEATED_FLAG,))

    def test_final_boss_is_tuned_as_a_real_group_boss(self):
        self.assertGreaterEqual(OPEN_EYED_FRAGMENT.max_hp, 600)
        self.assertGreaterEqual(OPEN_EYED_FRAGMENT.armor_class, 18)
        self.assertGreaterEqual(OPEN_EYED_FRAGMENT.auto_attack_damage, 15)
        self.assertGreaterEqual(OPEN_EYED_FRAGMENT.xp_reward, 500)

    def test_three_distinct_players_drive_lens_gate_orrery_and_seal(self):
        database = _FakeDatabase()
        party = [_Session(database, index, OBS_LENS_GALLERY_KEY) for index in (1, 2, 3)]
        for session in party:
            session.party = party
            database.quests[session.character.id] = {
                "status": "active",
                "current_step": "align_lenses",
            }

        async def scenario():
            await _align_lens(party[0], "north")
            await _align_lens(party[1], "south")
            await _align_lens(party[2], "zenith")

            for member in party:
                self.assertIn(LENSES_ALIGNED_FLAG, database.flags[member.character.id])
                self.assertEqual(database.quests[member.character.id]["current_step"], "sync_gate")
                member.character.current_room = OBS_THREE_HAND_GATE_KEY

            await _synchronize_gate(party[0])
            for member in party:
                self.assertIn(CORE_GATE_FLAG, database.flags[member.character.id])
                self.assertEqual(database.quests[member.character.id]["current_step"], "align_orrery")
                member.character.current_room = OBS_NULL_ORRERY_KEY

            await _turn_orrery(party[0], "inner")
            await _turn_orrery(party[1], "middle")
            await _turn_orrery(party[2], "outer")
            for member in party:
                self.assertIn(ORRERY_ALIGNED_FLAG, database.flags[member.character.id])
                self.assertEqual(database.quests[member.character.id]["current_step"], "defeat_fragment")
                database.quests[member.character.id]["current_step"] = "seal_aperture"
                database.grant_flag(member.character.id, BOSS_DEFEATED_FLAG)
                member.character.current_room = OBS_SEAL_ENGINE_KEY

            await _seal_aperture(party[0])
            for member in party:
                self.assertIn(APERTURE_SEALED_FLAG, database.flags[member.character.id])
                self.assertEqual(database.quests[member.character.id]["current_step"], "return_archivist")

        asyncio.run(scenario())


if __name__ == "__main__":
    unittest.main()
